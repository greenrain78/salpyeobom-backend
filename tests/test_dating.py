from datetime import date

from scripts.dating import distribute_dates

END = date(2026, 6, 7)


def test_sum_and_window():
    keys = [f"SYN-{i:05d}" for i in range(1363)]
    out = distribute_dates(keys, END, window_days=30)
    assert len(out) == 1363  # 모든 키 배정
    days = sorted({date.fromisoformat(v) for v in out.values()})
    assert days[0] >= date(2026, 5, 9)  # 30일 창 시작
    assert days[-1] <= END  # 종료일 이내


def test_non_uniform():
    keys = [f"k{i}" for i in range(1363)]
    out = distribute_dates(keys, END, window_days=30)
    counts: dict[str, int] = {}
    for v in out.values():
        counts[v] = counts.get(v, 0) + 1
    vals = list(counts.values())
    # 균등(=모두 동일)이 아니어야 한다 → 분산 > 0
    assert len(set(vals)) > 1
    assert max(vals) != min(vals)


def test_deterministic():
    keys = [f"k{i}" for i in range(200)]
    a = distribute_dates(keys, END, window_days=30)
    b = distribute_dates(list(reversed(keys)), END, window_days=30)
    assert a == b  # 입력 순서와 무관, 동일 결과


def test_empty():
    assert distribute_dates([], END) == {}
