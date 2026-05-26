"""ADL raw record value-transform helpers used by both list and detail responses."""

from __future__ import annotations

OUTGOING_SENTINEL_VALUES = frozenset({254, 255})


def clean_outgoing_minute(outgoing_1_list: list[int] | None) -> list[int] | None:
    """Replace 254/255 sensor sentinel values with 0. Returns None for missing or malformed input."""
    if not outgoing_1_list or len(outgoing_1_list) != 1440:
        return None
    return [0 if v in OUTGOING_SENTINEL_VALUES else int(v) for v in outgoing_1_list]


def aggregate_outgoing_to_24h(outgoing_1_list: list[int] | None) -> list[int] | None:
    """Sum cleaned minute series into 24 hourly buckets (60 minutes each)."""
    cleaned = clean_outgoing_minute(outgoing_1_list)
    if cleaned is None:
        return None
    return [sum(cleaned[h * 60 : (h + 1) * 60]) for h in range(24)]


def recount_outgoing_count_d(outgoing_1_list: list[int] | None) -> int | None:
    """Recount outgoing events from cleaned series — rising edges from 0 to >0 minute samples."""
    cleaned = clean_outgoing_minute(outgoing_1_list)
    if cleaned is None:
        return None
    count = 0
    prev = 0
    for v in cleaned:
        if v > 0 and prev == 0:
            count += 1
        prev = v
    return count


def aggregate_sleep_depth_to_24h(sleep_depth_1_list: list[int] | None) -> list[float] | None:
    """Average sleep depth minute samples into 24 hourly buckets."""
    if not sleep_depth_1_list or len(sleep_depth_1_list) != 1440:
        return None
    return [sum(sleep_depth_1_list[h * 60 : (h + 1) * 60]) / 60.0 for h in range(24)]


def normalize_recipient_id(value: str) -> str:
    """Normalize legacy floating-point recipient ids like '661.0' to '661'."""
    if value.endswith(".0") and value[:-2].isdigit():
        return value[:-2]
    return value
