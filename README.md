# kulms

`kulms` は、京都大学の学習支援システム KULMS にアクセスするための Python クライアントと CLI です。KULMS は Sakai LMS 互換の環境です。

Sakai Direct API を直接扱う代わりに、授業、授業資料、課題、お知らせ、カレンダーなど、KULMS の利用者が画面上で見慣れた単位で操作できる API と CLI を提供します。専用 API がまだない Direct API も `client.direct` や `kulms direct` から直接呼び出せます。

## 使い方

CLI として使うだけなら、基本の流れは次の通りです。

```powershell
uv tool install kulms
uv tool update-shell
kulms auth login
kulms courses
kulms assignments
```

`kulms courses` に表示される ID を使うと、授業資料を一覧表示したりダウンロードしたりできます。

```powershell
kulms resources COURSE_ID
kulms resources COURSE_ID --download
```

Python ライブラリとして使う場合は `python -m pip install kulms` を使ってください。`uv` を使わない場合は `pipx install kulms` でも CLI をインストールできます。

## 主な機能

- kuauth を使って KULMS にログインできます。
- ユーザー名、パスワード、TOTP シークレットを keyring に保存できます。
- セッション Cookie をユーザーキャッシュディレクトリに保存し、通常の CLI 操作では再ログインせずに使い回せます。
- コース一覧、コース詳細、コースのタブ構成を取得できます。
- 授業資料（KULMS 画面上の「リソース」）を一覧表示、またはコース別ディレクトリにダウンロードできます。
- 課題を全コース横断、またはコース指定で取得できます。
- 課題をステータスや締切日で絞り込めます。
- お知らせを全コース横断、またはコース指定で取得できます。
- お知らせを日数、件数、作成日で絞り込めます。
- カレンダーを全コース横断、またはコース指定で取得できます。
- Direct API の任意パスを直接呼び出せます。
- Pydantic v2 モデルとしてレスポンスを扱えます。

## 用語

Sakai の API では授業が `site`、授業資料が `content` と呼ばれます。このライブラリと CLI では、KULMS の画面上で見慣れた言葉に合わせて主に次の名前を使います。

| Sakai Direct API | kulms での名前 | 意味 |
| --- | --- | --- |
| `site` | `course` | 授業、コース |
| `content` | `resources` | 授業資料、KULMS 上の「リソース」 |
| `assignment` | `assignments` | 課題 |
| `announcement` | `announcements` | お知らせ |
| `calendar` | `calendar` | カレンダー |

CLI の引数は `COURSE_ID` と表示されます。これは `kulms courses` で表示されるコース ID です。

## インストール

Python 3.12 以上を前提にしています。PyPI からインストールする場合は次の通りです。

```powershell
python -m pip install kulms
```

CLI として普段使いする場合は、アプリケーションとして分離して入れられる `uv tool install` も便利です。

```powershell
uv tool install kulms
```

初回だけ、uv の tool 用ディレクトリを `PATH` に入れます。すでに設定済みなら不要です。

```powershell
uv tool update-shell
```

PowerShell を開き直したあと、どこからでも次のように実行できます。

```powershell
kulms --help
kulms auth status
kulms courses
```

pipx を使う場合は次の通りです。

```powershell
pipx install kulms
```

ライブラリとして使う場合も `pip install kulms` で同じパッケージを使います。`kulms` コマンドを配布しているため、CLI 依存関係は通常依存に含めています。

開発環境を用意する場合は、リポジトリを clone して次を実行します。

```powershell
uv sync --group dev
```

開発中の作業ツリーを CLI として入れる場合は次の通りです。

```powershell
uv tool install --editable .
```

アンインストールする場合は次の通りです。

```powershell
uv tool uninstall kulms
```
## CLIの使い方
### 初期設定

CLIを使うにはまず最初にログインします。

```powershell
kulms auth login
```

ログイン時に入力するものは次の通りです。

| 入力 | 保存先 | 備考 |
| --- | --- | --- |
| Username | keyring | 京都大学 ECS-ID などです。 |
| Password | keyring | `getpass.getpass()` で非表示入力します。 |
| TOTP secret | keyring | 保存を選んだ場合だけ保存します。 |
| One-time password | 保存しません | TOTP secret を保存しない場合に入力します。 |

TOTP シークレットは [京大の多要素認証マニュアル](https://www.iimc.kyoto-u.ac.jp/ja/services/account/mfa/manuals) に従って認証アプリを登録する際の QR に埋め込まれた `otpauth://totp/...?secret=XXXX&...` の `secret` パラメータです。登録後は QR が再表示されないので、登録画面で控えておくか、一度アプリを解除して再登録してください。

TOTP シークレットを保存すると、`kulms auth refresh` 時にワンタイムパスワードを手で入力しなくてよくなります。一方で、CLI が実質的に認証アプリ相当の情報を持つことになります。共有 PC や管理外の端末では保存しない方が安全です。

### 認証とセッション

CLI は資格情報とセッションを分けて扱います。

| 種類 | 保存場所 | 削除コマンド |
| --- | --- | --- |
| ユーザー名 | keyring | `kulms auth forget` |
| パスワード | keyring | `kulms auth forget` |
| TOTP シークレット | keyring | `kulms auth forget` |
| セッション Cookie | ユーザーキャッシュディレクトリ | `kulms auth logout` または `kulms auth forget` |

セッション Cookie の実際のパスは `kulms auth status` で確認できます。Windows では通常 `%LOCALAPPDATA%` 配下に保存されます。

セッション Cookie はログイン済みセッションとして扱える情報です。保存時は原子的に書き込み、可能な環境では所有者だけが読める権限にしますが、共有端末では `kulms auth logout` または `kulms auth forget` で削除してください。

通常の CLI コマンドは、セッションが切れても裏で勝手に再ログインしません。セッション切れになった場合は明示的に次を実行します。

```powershell
kulms auth refresh
```

完全にログインし直す場合は次を実行します。

```powershell
kulms auth login
```

セッションだけ消す場合は次の通りです。keyring の資格情報は残ります。

```powershell
kulms auth logout
```

資格情報とセッションを両方消す場合は次の通りです。

```powershell
kulms auth forget
```

現在の状態は次で確認できます。

```powershell
kulms auth status
```

### プロファイル

複数アカウントや検証環境を分けたい場合は `--profile` を使います。

```powershell
kulms --profile main auth login
kulms --profile main courses
```

プロファイルごとに keyring のサービス名とセッション Cookie ファイルが分かれます。デフォルトのプロファイル名は `default` です。

### コース一覧

```powershell
kulms courses
```

コース ID、コース名、種別を表示します。以降の `COURSE_ID` にはここに表示される ID を使います。

JSON で取得する場合は次の通りです。

```powershell
kulms courses --json
```

### コース詳細

```powershell
kulms course show COURSE_ID
```

コース名、コース ID、説明があれば説明を表示します。

### コースのタブ一覧

```powershell
kulms course tabs COURSE_ID
```

KULMS の授業ページ左側に出る「概要」「カレンダー」「お知らせ」「授業資料（リソース）」「課題」「小テスト」などのタブと、その裏側の Sakai tool ID を表示します。

例として、小テストは `sakai.samigo` として見えることがあります。小テスト API 自体は現時点の高水準ラッパーでは未対応ですが、Direct API ドキュメントには `sam_pub`、`sam_core`、`sam_item` などの関連エンティティがあります。

### 授業資料、リソースの一覧

```powershell
kulms resources COURSE_ID
```

KULMS 上で「リソース」と表示される授業資料を一覧表示します。フォルダは `folder`、ファイルは `file` として表示します。

### 授業資料、リソースのダウンロード

```powershell
kulms resources COURSE_ID --download
```

デフォルトではカレントディレクトリの `KULMS` 配下に次の構造で保存します。

```text
KULMS/
  Course Title/
    Folder Name/
      file.pdf
```

保存先を変える場合は `--dest` を使います。

```powershell
kulms resources COURSE_ID --download --dest .\downloads
```

実際に保存せず、保存予定だけ確認する場合は `--dry-run` を使います。

```powershell
kulms resources COURSE_ID --download --dry-run
```

既存ファイルはデフォルトでスキップします。上書きする場合は `--overwrite` を使います。

```powershell
kulms resources COURSE_ID --download --overwrite
```

デフォルトでは `https://lms.gakusei.kyoto-u.ac.jp/access/content/` 配下のファイルだけをダウンロードします。リソースに外部リンクが含まれている場合はスキップします。外部 URL も取得したい場合だけ、明示的に `--allow-external` を付けてください。

```powershell
kulms resources COURSE_ID --download --allow-external
```

1ファイルあたりの最大サイズはデフォルトで 512 MiB です。変更する場合は `--max-bytes` を使います。

```powershell
kulms resources COURSE_ID --download --max-bytes 104857600
```

ダウンロード結果のステータスは主に次の値です。

| ステータス | 意味 |
| --- | --- |
| `downloaded` | ダウンロードしました。 |
| `skipped` | 既存ファイルがある、または外部 URL のためスキップしました。 |
| `planned` | `--dry-run` による保存予定です。 |
| `failed` | HTTP エラーなどで失敗しました。 |

ファイル名やフォルダ名に Windows で使えない文字が含まれる場合は `_` に置き換えます。

### 課題一覧

全コース横断で課題を表示します。

```powershell
kulms assignments
```

コースを指定する場合は次の通りです。

```powershell
kulms assignments COURSE_ID
```

ステータスで絞り込む場合は `--status` を使います。

```powershell
kulms assignments --status OPEN
```

複数ステータスを指定する場合は `--status` を複数回指定します。

```powershell
kulms assignments --status OPEN --status DUE
```

締切日で絞り込む場合は `--from` と `--to` を使います。日付範囲は両端を含みます。

```powershell
kulms assignments --from 2026-04-20 --to 2026-04-30
```

ステータスと日付は同時に指定できます。

```powershell
kulms assignments --status OPEN --from 2026-04-20 --to 2026-05-10
```

### お知らせ一覧

全コース横断でお知らせを表示します。

```powershell
kulms announcements
```

コースを指定する場合は次の通りです。

```powershell
kulms announcements COURSE_ID
```

最近の日数で絞る場合は `--days` を使います。

```powershell
kulms announcements --days 7
```

最大件数を指定する場合は `--limit` を使います。

```powershell
kulms announcements --limit 20
```

作成日で絞り込む場合は `--from` と `--to` を使います。

```powershell
kulms announcements --from 2026-04-01 --to 2026-04-30
```

### カレンダー

全コース横断でカレンダーイベントを表示します。

```powershell
kulms calendar
```

コースを指定する場合は次の通りです。

```powershell
kulms calendar COURSE_ID
```

日付範囲を指定する場合は `--from` と `--to` を使います。

```powershell
kulms calendar --from 2026-04-01 --to 2026-04-30
```

Sakai Direct API のパラメータ名に合わせて `--first-date` と `--last-date` も使えます。

```powershell
kulms calendar --first-date 2026-04-01 --last-date 2026-04-30
```

### ダッシュボード

課題、お知らせ、カレンダーをまとめて表示します。

```powershell
kulms dashboard
```

現時点では簡易表示です。詳細な絞り込みや機械処理には `assignments`、`announcements`、`calendar` の各コマンドを使う方が向いています。

### Direct API を直接呼ぶ

高水準ラッパーがまだないエンドポイントは `kulms direct` で呼べます。

```powershell
kulms direct get site
kulms direct get /direct/site.json
kulms direct get /direct/user/current.json
```

JSON として表示できるレスポンスは自動的に整形されます。生レスポンスを見たい場合は `--raw` を使います。

```powershell
kulms direct get /direct/site.json --raw
```

`/direct/describe` を見る場合は次の通りです。

```powershell
kulms direct describe
```

特定 prefix の describe を見る場合は次の通りです。

```powershell
kulms direct describe assignment
kulms direct describe content
```

### JSON 出力

多くの CLI コマンドは `--json` をサポートしています。

```powershell
kulms assignments --status OPEN --json
kulms resources COURSE_ID --download --dry-run --json
```

JSON 出力では Pydantic モデルを `model_dump(mode="json", by_alias=True)` 相当で出力します。Sakai の camelCase フィールド名をできるだけ保った JSON になります。

## ライブラリの使い方

以下に最小例を示します。

```python
from kulms import KULMSClient

client = KULMSClient.from_credentials(
    username="USERNAME",
    password="PASSWORD",
    totp_secret="TOTP_SECRET",
)

session = client.sessions.current()
courses = client.courses.list()
assignments = client.assignments.list()
```

`KULMSClient` はコンテキストマネージャとしても使えます。

```python
from kulms import KULMSClient

with KULMSClient.from_credentials(username, password, totp_secret=totp_secret) as client:
    for course in client.courses.list():
        print(course.id, course.title)
```

ワンタイムパスワードを直接渡す場合は次の通りです。

```python
client = KULMSClient.from_credentials(
    username,
    password,
    onetime_password="123456",
)
```

必要になったタイミングで OTP を取得したい場合は `otp_callback` を渡せます。

```python
client = KULMSClient.from_credentials(
    username,
    password,
    otp_callback=lambda: input("OTP: "),
)
```

### ライブラリでのセッション保存

ライブラリ側でも `JsonFileSessionStore` を使って Cookie を保存できます。

```python
from pathlib import Path

from kulms import AuthExpiredError, KULMSClient
from kulms.session import JsonFileSessionStore

store = JsonFileSessionStore(Path("kulms.cookies.json"))

client = KULMSClient.from_credentials(
    username,
    password,
    totp_secret=totp_secret,
    session_store=store,
    load_session=True,
    trust_loaded_session=True,
)

try:
    client.sessions.current()
except AuthExpiredError:
    client = KULMSClient.from_credentials(
        username,
        password,
        totp_secret=totp_secret,
        session_store=store,
        load_session=False,
    )
    client.sessions.current()
    client.save_session()
```

`load_session=True` は保存済み Cookie を読み込みます。`trust_loaded_session=True` の場合、読み込んだ Cookie があると kuauth の内部ログイン状態を「準備済み」として扱い、不要な SSO フローを避けます。

保存済み Cookie は期限切れのものを読み飛ばします。セッションがサーバー側で無効になっている場合は API 呼び出し時に `AuthExpiredError` が発生します。

### 高水準 API

#### `client.courses`

コース、Sakai の `site` を扱います。

| メソッド | 内容 |
| --- | --- |
| `list(limit=100, offset=0)` | コース一覧を取得します。Sakai の `_limit` と `_start` に対応します。 |
| `iter(page_size=100)` | ページングしながらコースを順に yield します。 |
| `get(site_id, include_groups=False)` | コース詳細を取得します。 |
| `tabs(site_id, props=False, config=False)` | コースのページ、タブ、ツール一覧を取得します。 |
| `exists(site_id)` | コースが存在するか確認します。 |

例です。

```python
courses = client.courses.list(limit=50)

for course in client.courses.iter(page_size=100):
    print(course.id, course.title)

tabs = client.courses.tabs("COURSE_ID")
```

#### `client.resources`

授業資料、KULMS 上の「リソース」を扱います。Sakai Direct API では `content` です。

| メソッド | 内容 |
| --- | --- |
| `list(site_id)` | 指定コースのリソース一覧を取得します。 |
| `list_my()` | 自分に関連するリソース一覧を取得します。 |
| `download(site_id, dest="KULMS", overwrite=False, dry_run=False, allow_external=False, max_file_size=536870912)` | 指定コースのファイルをダウンロードします。 |

`download()` はフォルダ、つまり collection を保存対象から除外し、ファイルだけを保存します。保存先は `dest / course title / resource path` です。デフォルトでは KULMS の `/access/content/` 配下だけを取得し、外部 URL はスキップします。

```python
items = client.resources.list("COURSE_ID")

results = client.resources.download(
    "COURSE_ID",
    dest="KULMS",
    dry_run=True,
)
```

#### `client.assignments`

課題を扱います。

| メソッド | 内容 |
| --- | --- |
| `list(site_id=None, limit=None, offset=None, status=None, from_date=None, to_date=None)` | 課題一覧を取得します。 |
| `get(assignment_id)` | 課題 ID で課題を取得します。 |

`site_id=None` の場合は `/direct/assignment/my` を使い、全コース横断の課題を取得します。`site_id` を指定した場合は `/direct/assignment/site/{site_id}` を使います。

`status` は文字列または文字列リストを受け取ります。比較は大文字小文字を無視します。

`from_date` と `to_date` は締切日での絞り込みです。文字列、`date`、`datetime`、epoch 秒、epoch ミリ秒を扱えます。日付範囲は両端を含みます。

```python
open_assignments = client.assignments.list(status="OPEN")

upcoming = client.assignments.list(
    status=["OPEN", "DUE"],
    from_date="2026-04-20",
    to_date="2026-05-10",
)

course_assignments = client.assignments.list("COURSE_ID")
```

#### `client.announcements`

お知らせを扱います。

| メソッド | 内容 |
| --- | --- |
| `list(site_id=None, days=None, limit=None, from_date=None, to_date=None)` | お知らせ一覧を取得します。 |
| `motd(days=None, limit=None)` | 今日のお知らせを取得します。 |

`site_id=None` の場合は `/direct/announcement/user` を使い、全コース横断のお知らせを取得します。`site_id` を指定した場合は `/direct/announcement/site/{site_id}` を使います。

`days` は Sakai の `d` パラメータ、`limit` は `n` パラメータに対応します。`from_date` と `to_date` は `createdOn` に対するローカル日付での絞り込みです。

```python
announcements = client.announcements.list(limit=20)
recent = client.announcements.list(days=7)
course_news = client.announcements.list("COURSE_ID")
```

#### `client.calendar`

カレンダーイベントを扱います。

| メソッド | 内容 |
| --- | --- |
| `list(site_id=None, first_date=None, last_date=None)` | カレンダーイベント一覧を取得します。 |

`site_id=None` の場合は `/direct/calendar/my` を使い、全コース横断のイベントを取得します。`site_id` を指定した場合は `/direct/calendar/site/{site_id}` を使います。

```python
events = client.calendar.list(first_date="2026-04-01", last_date="2026-04-30")
course_events = client.calendar.list("COURSE_ID")
```

#### `client.users`

現在のユーザー情報を扱います。

| メソッド | 内容 |
| --- | --- |
| `current()` | `/direct/user/current` を取得します。 |

```python
user = client.users.current()
print(user.eid, user.display_name)
```

#### `client.sessions`

現在の Sakai セッション情報を扱います。

| メソッド | 内容 |
| --- | --- |
| `current()` | `/direct/session/current` を取得します。 |

```python
session = client.sessions.current()
print(session.user_eid, session.active)
```

#### `client.direct`

未ラップの Sakai Direct API を呼ぶ低水準クライアントです。

| メソッド | 内容 |
| --- | --- |
| `request(method, path_or_url, 追加キーワード引数)` | kuauth の KULMS サービス経由で HTTP リクエストを送ります。 |
| `get_json(path_or_url, params=None, ensure_json_suffix=True)` | GET して JSON として返します。 |
| `post_json(path_or_url, data=None, json_data=None, params=None, ensure_json_suffix=True)` | POST して JSON として返します。 |

パスは次のように正規化されます。

| 入力例 | 実際の扱い |
| --- | --- |
| `site` | `/direct/site.json` |
| `/site` | `/direct/site.json` |
| `/direct/site` | `/direct/site.json` |
| `/direct/site.json` | `/direct/site.json` |
| `/access/content/...` | `/access/content/...` |
| `https://...` | 絶対 URL として扱います。 |

`request()` は `/access` や `/portal` も保持するため、リソースファイルのダウンロードに使えます。

```python
raw_sites = client.direct.get_json("site")
assignment_doc = client.direct.get_json("/direct/assignment/my")
response = client.direct.request("GET", "/access/content/group/example/file.pdf")
```

### ライブラリ内のモデル

モデルは Pydantic v2 の `BaseModel` を継承しています。`extra="allow"` なので、現在モデルに定義していない Sakai の追加フィールドも落とさず保持します。`populate_by_name=True` なので、Python 側の snake_case 名と Sakai 側の alias 名の両方を受け取れます。

| モデル | 主なフィールド |
| --- | --- |
| `Course` | `id`, `title`, `type`, `description`, `entity_id`, `entity_title`, `entity_url` |
| `CourseTab` | `id`, `title`, `site_id`, `url`, `tools` |
| `CourseTool` | `id`, `title`, `tool_id`, `placement_id`, `site_id`, `page_id`, `url` |
| `ResourceItem` | `id`, `title`, `name`, `type`, `url`, `path`, `container`, `size`, `children` |
| `DownloadResult` | `source_url`, `path`, `status`, `bytes`, `message` |
| `Assignment` | `id`, `title`, `context`, `status`, `instructions`, `due_time`, `due_time_string`, `open_time`, `close_time` |
| `Announcement` | `id`, `announcement_id`, `title`, `body`, `site_id`, `site_title`, `created_on`, `created_by_display_name` |
| `CalendarEvent` | `event_id`, `title`, `description`, `site_id`, `site_name`, `first_time`, `duration`, `type` |
| `SessionInfo` | `id`, `active`, `user_id`, `user_eid`, `creation_time`, `current_time`, `last_accessed_time`, `max_inactive_interval` |
| `User` | `id`, `eid`, `display_id`, `display_name`, `email`, `first_name`, `last_name`, `type` |

`ResourceItem` には便利なプロパティがあります。

| プロパティ | 内容 |
| --- | --- |
| `display_name` | `title`, `name`, `id` の順に表示名を返します。 |
| `download_url` | `webLinkUrl`, `downloadUrl`, `contentUrl`, `url`, `entityURL` などからダウンロード URL を推定します。 |
| `is_collection` | フォルダ相当の collection かどうかを返します。 |

### ライブラリ内の例外

公開されている例外は次の通りです。

| 例外 | 意味 |
| --- | --- |
| `KULMSError` | このパッケージの基底例外です。 |
| `AuthExpiredError` | セッション切れ、未認可、認証ページへのリダイレクトなどで発生します。 |
| `APIError` | JSON でないレスポンス、HTTP エラー、不正 JSON などで発生します。 |
| `NotFoundError` | HTTP 404 の場合に発生します。`APIError` のサブクラスです。 |

CLI では `AuthExpiredError` を検出すると、`kulms auth login` を促して終了コード 2 で終了します。その他の `KULMSError` は終了コード 1 です。

## License

MIT — see [LICENSE](LICENSE).