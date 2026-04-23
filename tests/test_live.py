from __future__ import annotations

import os

import pytest

from kulms import KULMSClient


pytestmark = pytest.mark.skipif(os.environ.get("KULMS_LIVE_TEST") != "1", reason="live KULMS test disabled")


def test_live_sessions_and_courses() -> None:
    username = os.environ["KUAUTH_USERNAME"]
    password = os.environ["KUAUTH_PASSWORD"]
    totp_secret = os.environ.get("KUAUTH_TOTP_SECRET")
    onetime_password = os.environ.get("KUAUTH_ONETIME_PASSWORD")
    client = KULMSClient.from_credentials(
        username,
        password,
        totp_secret=totp_secret,
        onetime_password=onetime_password,
    )

    session = client.sessions.current()
    courses = client.courses.list(limit=20)

    assert session.user_eid or session.user_id
    assert isinstance(courses, list)
