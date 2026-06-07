"""보고서 생성일(generated_at) 분산 유틸 — 결정적·비균등.

주의: 이 날짜는 **연출**이다. 이상탐지 detected_at 은 단일 배치(한 시각)라 날짜별
근거가 없으므로, 데모가 자연스러워 보이도록 인위적으로 최근 N일에 비균등 분산한다.
난수를 쓰지 않고(재현 가능) 대상자 id 해시로 배정한다.
"""

from __future__ import annotations

from datetime import date, timedelta

# 요일 가중(월~일; date.weekday() Mon=0). 주말은 낮게.
_WEEKDAY_W = [1.0, 1.0, 1.0, 1.0, 1.0, 0.45, 0.4]

# 결정적 지터 시퀀스(난수 대체) — 일별 건수에 변동을 주기 위함.
_JITTER = [
    1.0, 0.7, 1.3, 0.9, 1.15, 0.8, 1.25, 0.6, 1.1, 0.95,
    1.2, 0.75, 1.05, 0.85, 1.3, 0.65, 1.1, 0.9, 1.2, 0.7,
    1.0, 1.25, 0.8, 1.15, 0.6, 1.3, 0.95, 0.75, 1.1, 0.9,
]


def _key_hash(k: str) -> int:
    h = 0
    for ch in k:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def distribute_dates(
    keys: list[str], end: date, window_days: int = 30
) -> dict[str, str]:
    """keys 를 [end-(window_days-1) .. end] 에 비균등·결정적으로 배정.

    Returns: {key: 'YYYY-MM-DD'}. 합계는 정확히 len(keys), 모든 날짜는 창 내,
    일별 건수는 요일·최근가중·지터로 변동(균등 아님).
    """
    n = len(keys)
    if n == 0:
        return {}
    days = [end - timedelta(days=window_days - 1 - i) for i in range(window_days)]

    # 일별 가중치
    weights = []
    for i, d in enumerate(days):
        recency = 1.0 + 0.4 * (i / (window_days - 1)) if window_days > 1 else 1.0
        weights.append(_WEEKDAY_W[d.weekday()] * recency * _JITTER[i % len(_JITTER)])
    total_w = sum(weights)

    # 최대잉여법으로 일별 정원 산정 (합계 == n)
    raw = [n * w / total_w for w in weights]
    quota = [int(x) for x in raw]
    remainder = n - sum(quota)
    by_frac = sorted(range(window_days), key=lambda i: raw[i] - quota[i], reverse=True)
    for i in range(remainder):
        quota[by_frac[i]] += 1

    # 결정적 배정: id 해시로 정렬 후 과거→종료일 정원만큼 채움
    ordered = sorted(keys, key=_key_hash)
    result: dict[str, str] = {}
    idx = 0
    for di, q in enumerate(quota):
        for _ in range(q):
            result[ordered[idx]] = days[di].isoformat()
            idx += 1
    return result
