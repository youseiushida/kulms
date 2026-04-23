from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from rich import box
from typing import Any

import keyring
import typer
from platformdirs import user_cache_dir
from rich.console import Console
from rich.table import Column, Table

from kulms import AuthExpiredError, KULMSClient, KULMSError
from kulms.models import KULMSModel
from kulms.resources.resources import DEFAULT_MAX_FILE_SIZE
from kulms.session import JsonFileSessionStore


app = typer.Typer(help="KULMS Direct API client.")
auth_app = typer.Typer(help="Manage credentials and cached sessions.")
course_app = typer.Typer(help="Inspect courses and course tabs.")
direct_app = typer.Typer(help="Call Sakai Direct API endpoints.")
app.add_typer(auth_app, name="auth")
app.add_typer(course_app, name="course")
app.add_typer(direct_app, name="direct")

console = Console()
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class CLIState:
    profile = "default"


state = CLIState()


@app.callback()
def main(profile: str = typer.Option("default", "--profile", "-p", help="Credential profile name.")) -> None:
    state.profile = profile


def _service_name(profile: str | None = None) -> str:
    return f"kulms:{profile or state.profile}"


def _session_path(profile: str | None = None) -> Path:
    return Path(user_cache_dir("kulms")) / f"{profile or state.profile}.cookies.json"


def _session_store(profile: str | None = None) -> JsonFileSessionStore:
    return JsonFileSessionStore(_session_path(profile))


def _get_secret(key: str, *, profile: str | None = None) -> str | None:
    return keyring.get_password(_service_name(profile), key)


def _set_secret(key: str, value: str, *, profile: str | None = None) -> None:
    keyring.set_password(_service_name(profile), key, value)


def _delete_secret(key: str, *, profile: str | None = None) -> None:
    try:
        keyring.delete_password(_service_name(profile), key)
    except keyring.errors.PasswordDeleteError:
        return


def _credentials(*, require_totp: bool = False) -> dict[str, str]:
    username = _get_secret("username")
    password = _get_secret("password")
    totp_secret = _get_secret("totp_secret")
    missing = [name for name, value in {"username": username, "password": password}.items() if not value]
    if require_totp and not totp_secret:
        missing.append("totp_secret")
    if missing:
        raise typer.BadParameter(f"Missing credentials in keyring: {', '.join(missing)}. Run `kulms auth login`.")
    data = {"username": username or "", "password": password or ""}
    if totp_secret:
        data["totp_secret"] = totp_secret
    return data


def _client(*, require_cached_session: bool = True) -> KULMSClient:
    creds = _credentials()
    store = _session_store()
    client = KULMSClient.from_credentials(
        creds["username"],
        creds["password"],
        totp_secret=creds.get("totp_secret"),
        session_store=store,
        load_session=True,
        trust_loaded_session=True,
    )
    if require_cached_session and not client.has_cached_session:
        raise AuthExpiredError("No cached session. Run `kulms auth login`.")
    return client


def _explicit_login_client(*, otp: str | None = None) -> KULMSClient:
    creds = _credentials()
    return KULMSClient.from_credentials(
        creds["username"],
        creds["password"],
        totp_secret=creds.get("totp_secret") if otp is None else None,
        onetime_password=otp,
        session_store=_session_store(),
        load_session=False,
    )


def _print_json(value: Any) -> None:
    payload = _jsonable(value)
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _jsonable(value: Any) -> Any:
    if isinstance(value, KULMSModel):
        return _jsonable(value.model_dump(mode="json", by_alias=True))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _table(*columns: str | Column, expand: bool = True) -> Table:
    rendered_columns = [
        column if isinstance(column, Column) else Column(column, overflow="fold")
        for column in columns
    ]
    return Table(*rendered_columns, box=box.SIMPLE, expand=expand)


def _course_titles(client: KULMSClient) -> dict[str, str]:
    try:
        return {course.id or "": course.title or course.entity_title or course.id or "" for course in client.courses.list(limit=500)}
    except KULMSError:
        return {}


def _course_label(course_id: str | None, course_titles: dict[str, str]) -> str:
    if not course_id:
        return ""
    title = course_titles.get(course_id)
    return f"{title} ({course_id})" if title and title != course_id else course_id


def _event_time(value: object) -> str:
    if isinstance(value, dict):
        display = value.get("display")
        if display:
            return str(display)
        time_value = value.get("time")
        if time_value:
            return _display_time(time_value)
        epoch_second = value.get("epochSecond")
        if epoch_second:
            return _display_time(epoch_second)
    return _display_time(value)


def _display_time(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, int | float):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return _display_time(int(text))
        if text.endswith("Z") and "T" in text:
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                return dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except ValueError:
                return text
        return text
    return str(value or "")


def _display_path(path: Path | None) -> str:
    if path is None:
        return ""
    text = str(path)
    try:
        text = str(path.relative_to(Path.cwd()))
    except ValueError:
        pass
    return "./" + text.replace("\\", "/")


def _run_read(fn):
    try:
        return fn()
    except AuthExpiredError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print("Run: [bold]kulms auth login[/bold]")
        raise typer.Exit(2) from exc
    except KULMSError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


@auth_app.command("login")
def auth_login() -> None:
    username = typer.prompt("Username")
    password = getpass("Password: ")
    save_totp = typer.confirm("Save TOTP secret in keyring?", default=False)
    if save_totp:
        totp_secret = getpass("TOTP secret: ")
        otp = None
    else:
        totp_secret = None
        otp = typer.prompt("One-time password")

    _set_secret("username", username)
    _set_secret("password", password)
    if totp_secret:
        _set_secret("totp_secret", totp_secret)
    else:
        _delete_secret("totp_secret")

    client = _explicit_login_client(otp=otp)
    session = client.sessions.current()
    client.save_session()
    console.print(f"[green]Logged in as {session.user_eid or username}[/green]")


@auth_app.command("refresh")
def auth_refresh() -> None:
    otp = None
    if not _get_secret("totp_secret"):
        otp = typer.prompt("One-time password")
    client = _explicit_login_client(otp=otp)
    session = client.sessions.current()
    client.save_session()
    console.print(f"[green]Session refreshed for {session.user_eid or _get_secret('username')}[/green]")


@auth_app.command("status")
def auth_status() -> None:
    username = _get_secret("username")
    has_password = _get_secret("password") is not None
    has_totp = _get_secret("totp_secret") is not None
    session_file = _session_path()
    console.print(f"Profile: [bold]{state.profile}[/bold]")
    console.print(f"Username: {username or '[missing]'}")
    console.print(f"Password: {'stored' if has_password else 'missing'}")
    console.print(f"TOTP secret: {'stored' if has_totp else 'not stored'}")
    console.print(f"Session cache: {session_file if session_file.exists() else 'missing'}")
    if not username or not has_password or not session_file.exists():
        return
    try:
        client = _client(require_cached_session=True)
        session = client.sessions.current()
    except AuthExpiredError:
        console.print("[yellow]Session: expired[/yellow]")
        return
    console.print(f"[green]Session: active ({session.user_eid or session.user_id})[/green]")


@auth_app.command("logout")
def auth_logout() -> None:
    _session_store().clear()
    console.print("[green]Session cache deleted[/green]")


@auth_app.command("forget")
def auth_forget() -> None:
    _session_store().clear()
    for key in ("username", "password", "totp_secret"):
        _delete_secret(key)
    console.print("[green]Credentials and session cache deleted[/green]")


@app.command("courses")
def courses(json_output: bool = typer.Option(False, "--json", help="Print JSON.")) -> None:
    result = _run_read(lambda: _client().courses.list())
    if json_output:
        _print_json(result)
        return
    table = _table(
        Column("Course ID", no_wrap=True),
        Column("Course", overflow="fold", ratio=4),
        Column("Type", no_wrap=True),
    )
    for course in result:
        table.add_row(course.id or "", course.title or course.entity_title or "", course.type or "")
    console.print(table)


@course_app.command("show")
def course_show(course_id: str, json_output: bool = typer.Option(False, "--json", help="Print JSON.")) -> None:
    course = _run_read(lambda: _client().courses.get(course_id))
    if json_output:
        _print_json(course)
        return
    console.print(f"[bold]{course.title or course.entity_title or course_id}[/bold]")
    console.print(f"Course ID: {course.id or course_id}")
    if course.description:
        console.print(course.description)


@course_app.command("tabs")
def course_tabs(course_id: str, json_output: bool = typer.Option(False, "--json", help="Print JSON.")) -> None:
    client = _client()
    course = _run_read(lambda: client.courses.get(course_id))
    tabs = _run_read(lambda: client.courses.tabs(course_id))
    if json_output:
        _print_json(tabs)
        return
    console.print(f"[bold]{course.title or course.entity_title or course_id}[/bold]")
    console.print(f"Course ID: {course.id or course_id}")
    table = _table(
        Column("Tab", overflow="fold", ratio=2),
        Column("Tool IDs", overflow="fold", ratio=5),
    )
    for tab in tabs:
        table.add_row(tab.title or "", ", ".join(tool.tool_id or "" for tool in tab.tools))
    console.print(table)


@app.command("resources")
def resources(
    course_id: str,
    download: bool = typer.Option(False, "--download", help="Download listed resources."),
    dest: Path = typer.Option(Path("KULMS"), "--dest", help="Download destination."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan downloads without writing files."),
    allow_external: bool = typer.Option(False, "--allow-external", help="Download external resource URLs."),
    max_bytes: int | None = typer.Option(DEFAULT_MAX_FILE_SIZE, "--max-bytes", help="Maximum bytes per downloaded file."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    client = _client()
    course = _run_read(lambda: client.courses.get(course_id))
    if download:
        result = _run_read(
            lambda: client.resources.download(
                course_id,
                dest=dest,
                overwrite=overwrite,
                dry_run=dry_run,
                allow_external=allow_external,
                max_file_size=max_bytes,
            )
        )
        if json_output:
            _print_json(result)
            return
        console.print(f"[bold]{course.title or course.entity_title or course_id}[/bold]")
        console.print(f"Course ID: {course.id or course_id}")
        table = _table(
            Column("Status", no_wrap=True),
            Column("Saved to", overflow="fold", ratio=5),
            Column("Bytes", justify="right", no_wrap=True),
            Column("Message", overflow="fold", ratio=2),
            expand=True,
        )
        for item in result:
            table.add_row(
                item.status,
                _display_path(item.path),
                str(item.bytes or ""),
                item.message or "",
            )
        console.print(table)
        return
    result = _run_read(lambda: client.resources.list(course_id))
    if json_output:
        _print_json(result)
        return
    console.print(f"[bold]{course.title or course.entity_title or course_id}[/bold]")
    console.print(f"Course ID: {course.id or course_id}")
    table = _table(
        Column("Name", overflow="fold", ratio=4),
        Column("Kind", no_wrap=True),
        Column("Size", justify="right", no_wrap=True),
        Column("URL", overflow="fold", ratio=5),
    )
    for item in result:
        kind = "folder" if item.is_collection else "file"
        table.add_row(item.display_name, kind, str(item.size or ""), item.download_url or "")
    console.print(table)


@app.command("assignments")
def assignments(
    course_id: str | None = typer.Argument(None),
    status: list[str] | None = typer.Option(None, "--status", "-s", help="Filter by assignment status, e.g. OPEN, DUE, CLOSED."),
    from_date: str | None = typer.Option(None, "--from", help="Only assignments due on/after yyyy-mm-dd."),
    to_date: str | None = typer.Option(None, "--to", help="Only assignments due on/before yyyy-mm-dd."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    client = _client()
    course_titles = _course_titles(client)
    result = _run_read(lambda: client.assignments.list(course_id, status=status, from_date=from_date, to_date=to_date))
    if json_output:
        _print_json(result)
        return
    table = _table(
        Column("Title", overflow="fold", ratio=4),
        Column("Due", no_wrap=True),
        Column("Status", no_wrap=True),
        Column("Course", overflow="fold", ratio=5),
    )
    for item in result:
        due = item.due_time_string or item.due_time or ""
        table.add_row(item.title or "", _display_time(due), item.status or "", _course_label(item.context, course_titles))
    console.print(table)


@app.command("announcements")
def announcements(
    course_id: str | None = typer.Argument(None),
    days: int | None = typer.Option(None, "--days", help="Limit by recent days."),
    from_date: str | None = typer.Option(None, "--from", help="Only announcements created on/after yyyy-mm-dd."),
    to_date: str | None = typer.Option(None, "--to", help="Only announcements created on/before yyyy-mm-dd."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum items."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    client = _client()
    course_titles = _course_titles(client)
    result = _run_read(lambda: client.announcements.list(course_id, days=days, limit=limit, from_date=from_date, to_date=to_date))
    if json_output:
        _print_json(result)
        return
    table = _table(
        Column("Title", overflow="fold", ratio=4),
        Column("Course", overflow="fold", ratio=5),
        Column("Created", no_wrap=True),
    )
    for item in result:
        table.add_row(item.title or "", _course_label(item.site_id, course_titles), _display_time(item.created_on))
    console.print(table)


@app.command("calendar")
def calendar(
    course_id: str | None = typer.Argument(None),
    first_date: str | None = typer.Option(None, "--first-date", help="Only events on/after yyyy-mm-dd."),
    last_date: str | None = typer.Option(None, "--last-date", help="Only events on/before yyyy-mm-dd."),
    from_date: str | None = typer.Option(None, "--from", help="Alias for --first-date."),
    to_date: str | None = typer.Option(None, "--to", help="Alias for --last-date."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    client = _client()
    course_titles = _course_titles(client)
    first_date = from_date or first_date
    last_date = to_date or last_date
    result = _run_read(lambda: client.calendar.list(course_id, first_date=first_date, last_date=last_date))
    if json_output:
        _print_json(result)
        return
    table = _table(
        Column("Title", overflow="fold", ratio=4),
        Column("Course", overflow="fold", ratio=5),
        Column("Time", no_wrap=True),
        Column("Type", no_wrap=True),
    )
    for item in result:
        table.add_row(item.title or "", item.site_name or _course_label(item.site_id, course_titles), _event_time(item.first_time), item.type or "")
    console.print(table)


@app.command("dashboard")
def dashboard(json_output: bool = typer.Option(False, "--json", help="Print JSON.")) -> None:
    client = _client()
    course_titles = _course_titles(client)
    payload = _run_read(
        lambda: {
            "assignments": client.assignments.list(),
            "announcements": client.announcements.list(limit=10),
            "calendar": client.calendar.list(),
        }
    )
    if json_output:
        _print_json(payload)
        return
    console.rule("Assignments")
    for item in payload["assignments"]:
        due = item.due_time_string or item.due_time or ""
        console.print(f"- {_course_label(item.context, course_titles)}: {item.title or '(untitled)'} {_display_time(due)}")
    console.rule("Announcements")
    for item in payload["announcements"]:
        console.print(f"- {_course_label(item.site_id, course_titles)}: {item.title or '(untitled)'}")
    console.rule("Calendar")
    for item in payload["calendar"]:
        console.print(f"- {item.site_name or _course_label(item.site_id, course_titles)}: {item.title or '(untitled)'} {_event_time(item.first_time)}")


@direct_app.command("get")
def direct_get(
    path: str,
    raw: bool = typer.Option(False, "--raw", help="Print raw response body."),
    json_output: bool = typer.Option(False, "--json", help="Pretty-print JSON."),
) -> None:
    client = _client()
    if raw:
        response = _run_read(lambda: client.direct.request("GET", path))
        console.print(response.text)
        return
    result = _run_read(lambda: client.direct.get_json(path, ensure_json_suffix=not path.endswith(".json")))
    if json_output or isinstance(result, (dict, list)):
        _print_json(result)
    else:
        console.print(result)


@direct_app.command("describe")
def direct_describe(prefix: str | None = None) -> None:
    path = "/direct/describe" if prefix is None else f"/direct/{prefix}/describe"
    response = _run_read(lambda: _client().direct.request("GET", path))
    console.print(response.text)


if __name__ == "__main__":
    app()
