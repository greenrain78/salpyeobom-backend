"""Unit tests for app/services/adl_raw_transform pure functions."""

from app.services.adl_raw_transform import (
    aggregate_outgoing_to_24h,
    aggregate_sleep_depth_to_24h,
    clean_outgoing_minute,
    normalize_recipient_id,
    recount_outgoing_count_d,
)


def test_clean_outgoing_minute_none_input() -> None:
    assert clean_outgoing_minute(None) is None


def test_clean_outgoing_minute_wrong_length() -> None:
    assert clean_outgoing_minute([1, 2, 3]) is None


def test_clean_outgoing_minute_replaces_254_255() -> None:
    data = [0] * 1440
    data[0] = 5
    data[100] = 254
    data[200] = 255
    result = clean_outgoing_minute(data)
    assert result is not None
    assert result[0] == 5
    assert result[100] == 0
    assert result[200] == 0
    assert result[1] == 0


def test_aggregate_outgoing_to_24h_none() -> None:
    assert aggregate_outgoing_to_24h(None) is None


def test_aggregate_outgoing_to_24h_basic() -> None:
    data = [0] * 1440
    data[0] = 5  # minute 0 of hour 0
    data[30] = 254  # sentinel at minute 30 of hour 0 → cleaned to 0
    result = aggregate_outgoing_to_24h(data)
    assert result is not None
    assert len(result) == 24
    assert result[0] == 5  # only the 5 remains; sentinel cleaned to 0


def test_recount_outgoing_count_d_none() -> None:
    assert recount_outgoing_count_d(None) is None


def test_recount_outgoing_count_d_rising_edges() -> None:
    # Three rising edges: 0→1, 0→3, 0→2 (sentinels in between should not count)
    data = [0] * 1440
    # Edge 1: minute 10 goes 0→1, then back to 0 at minute 11
    data[10] = 1
    # Edge 2: minute 100 goes 0→3, then back to 0 at minute 101
    data[100] = 3
    # Sentinel at minute 200 (254) — should NOT count as rising edge
    data[200] = 254
    # Edge 3: minute 300 goes 0→2
    data[300] = 2
    result = recount_outgoing_count_d(data)
    assert result == 3


def test_aggregate_sleep_depth_to_24h_none() -> None:
    assert aggregate_sleep_depth_to_24h(None) is None


def test_aggregate_sleep_depth_to_24h_averages() -> None:
    data = [4] * 1440
    result = aggregate_sleep_depth_to_24h(data)
    assert result is not None
    assert len(result) == 24
    assert all(v == 4.0 for v in result)


def test_normalize_recipient_id_strips_dot_zero() -> None:
    assert normalize_recipient_id("661.0") == "661"
    assert normalize_recipient_id("R-001") == "R-001"
    assert normalize_recipient_id("12.5") == "12.5"
