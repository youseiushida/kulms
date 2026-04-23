from __future__ import annotations

from kulms.timeutils import is_date_in_range, value_to_local_date


def test_epoch_millis_to_local_date() -> None:
    assert value_to_local_date(1776743620543) is not None


def test_iso_range_is_inclusive() -> None:
    assert is_date_in_range("2026-04-30T01:30:00Z", from_date="2026-04-30", to_date="2026-04-30")
    assert not is_date_in_range("2026-04-29T01:30:00Z", from_date="2026-04-30")
