"""결정론적 익스팬더 — scenario_gen 의 daily 일과표를 adl_raw_records 60행으로 전개.

입력: generate(class, seed) 산출물(persona·scenario·daily[60]·records).
출력: adl_raw_records 컬럼을 채운 dict 60개(= 1명 × 60일).

분단위 1440 배열·시간단위 24 배열·스칼라 지표를 클래스별 관측 분포에 맞춰 전개하고,
마지막에 불변 시그니처를 강제(clamp)한다. 모든 정량 분포는 id 1~60 프로파일에서만
도출했다(상세 주석은 PROFILE).

scenario_gen 은 '무엇이 일어났는가'(활동 형태·이벤트·외출/목욕 유무)를 정하고,
expander 는 그것을 클래스 분포 내부의 '정량 수치'로 채운다. 즉 클래스 경계(시그니처)는
코드가 강제하고, 서사는 그 봉투 *안*의 디테일·추세만 흔든다.
"""

from __future__ import annotations

import datetime as dt
import random
from typing import Any

# id 1~60 에서 관측된 aix_1 비제로 이산 레벨(33 간격, 30단계). 비제로는 이 집합에서만.
AIX_LEVELS = [33 * k if k <= 2 else round(k * 1000 / 30) for k in range(1, 31)]
AIX_LEVELS = [33, 66, 100, 133, 166, 200, 233, 266, 300, 333, 366, 400, 433, 466,
              500, 533, 566, 600, 633, 666, 700, 733, 766, 800, 833, 866, 900, 933, 966, 1000]
# 비제로 레벨 가중치: 관측 평균 ~354 에 맞춰 중간(index~10, 333~366) 중심 종형.
_AIX_W = [max(0.02, 2.718 ** (-((k - 10) ** 2) / 60.0)) for k in range(30)]


# --------------------------------------------------------------------------- #
# 클래스 프로파일 (id 1~60 관측치)
# --------------------------------------------------------------------------- #
# place_code / outgoing / sleep_depth 분포는 관측 카운트를 정규화한 가중치.
PROFILE: dict[str, dict[str, Any]] = {
    "응급": {
        "source_type": "응급",
        "aix1_zero": 0.87,
        "place": {254: 15078, 0: 14222, 20: 8028, 1: 3301, 255: 2571},
        "outgoing": {255: 27593, 254: 15607},
        "sleep_depth": {0: 32363, 1: 3208, 2: 3116, 3: 117, 4: 4396},
        "aix_h_zero": 0.39, "aix_h_max": 759, "aix_h_mean": 55,
        "night_aix_env": (0.0, 20417.0),
    },
    "사망": {
        "source_type": "사망",
        "aix1_zero": 0.55,
        "place": {30: 29429, 10: 8667, 254: 4475, 255: 629},
        "outgoing": {255: 38116, 254: 4475, 0: 609},
        "sleep_depth": None,  # 사망 파일은 sleep_depth 전부 결측(None)
        "aix_h_zero": 0.09, "aix_h_max": 685, "aix_h_mean": 164,
        "night_aix_env": (0.0, 15.0),
    },
    "평시": {  # 라벨 없음 → 응급의 비이벤트 기저(살아있고 활동하는 사람)에서 외삽
        "source_type": "평소",
        "aix1_zero": 0.85,
        "place": {254: 15078, 0: 14222, 20: 8028, 1: 3301, 255: 2571},
        "outgoing": {255: 27593, 254: 15607},
        "sleep_depth": {0: 32363, 1: 3208, 2: 3116, 3: 117, 4: 4396},
        "aix_h_zero": 0.40, "aix_h_max": 400, "aix_h_mean": 50,
        "night_aix_env": (0.0, 60.0),
    },
}


# --------------------------------------------------------------------------- #
# 헬퍼
# --------------------------------------------------------------------------- #
def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _cat(rng: random.Random, dist: dict[int, float], k: int) -> list[int]:
    keys = list(dist)
    return rng.choices(keys, weights=[dist[x] for x in keys], k=k)


def _longest_zero_run(arr: list[int]) -> int:
    best = cur = 0
    for x in arr:
        cur = cur + 1 if x == 0 else 0
        best = max(best, cur)
    return best


# --------------------------------------------------------------------------- #
# 분단위 배열 전개
# --------------------------------------------------------------------------- #
def _expand_aix1(rng: random.Random, activity: list[int], zero_frac: float) -> tuple[list[int], list[int]]:
    """activity_by_hour(24, 0~3) 로 1440 aix_1 과 24 aix_h 를 만든다.

    비제로는 활동이 있는 시간대에 집중 → 응급 종반 야간활동 급등이 야간 aix 로 이어진다.
    전체 비제로 비율은 클래스 zero_frac 에 맞춘다.
    """
    w = {0: 0.10, 1: 0.7, 2: 1.3, 3: 2.0}
    hour_w = [w[a] for a in activity]
    sw = sum(hour_w) or 1.0
    target_nz = round((1 - zero_frac) * 1440)
    aix1 = [0] * 1440
    aix_h = [0] * 24
    for h in range(24):
        nz_h = min(60, round(target_nz * hour_w[h] / sw))
        if nz_h <= 0:
            continue
        mins = rng.sample(range(h * 60, h * 60 + 60), nz_h)
        levels = rng.choices(AIX_LEVELS, weights=_AIX_W, k=nz_h)
        s = 0
        for m, lv in zip(mins, levels):
            aix1[m] = lv
            s += lv
        aix_h[h] = round(s / 60)  # 시간 평균
    return aix1, aix_h


def _expand_sleep_depth(rng: random.Random, prof: dict, sleep: dict) -> list[int] | None:
    if prof["sleep_depth"] is None:
        return None  # 사망: 원본 결측 재현
    arr = _cat(rng, prof["sleep_depth"], 1440)
    # 수면창 동안 깊은 수면(3~4) 비율 상승 — 인과 일관성
    start, end = sleep["start_min"], sleep["end_min"]
    rng_mins = range(start, 1440) if start > end else range(start, end)
    night = list(rng_mins) + (list(range(0, end)) if start > end else [])
    for m in night:
        if rng.random() < 0.45:
            arr[m] = rng.choice([3, 4, 4])
    return arr


# --------------------------------------------------------------------------- #
# 환경 24시간 곡선
# --------------------------------------------------------------------------- #
def _diurnal(rng: random.Random, env: dict, klass: str) -> tuple[list, list, list]:
    t0, h0, ip = env["temp"], env["humi"], env["illu_peak"]
    temp, humi, illu = [], [], []
    for h in range(24):
        # 온도: 새벽 최저, 오후 2~3시 최고
        dt_ = -1.5 + 3.0 * max(0.0, 1 - abs(h - 14) / 10.0)
        temp.append(round(_clamp(t0 + dt_ + rng.uniform(-0.4, 0.4), 21.9, 32.8), 1))
        humi.append(round(_clamp(h0 - dt_ * 1.5 + rng.uniform(-2, 2), 42.3, 71.7), 1))
        # 조도: 주간만, 정오 피크
        day = max(0.0, 1 - abs(h - 12) / 7.0)
        illu.append(round(_clamp(ip * day + rng.uniform(-3, 3), 0, 125), 1))
    return temp, humi, illu


# --------------------------------------------------------------------------- #
# 하루 1행 전개
# --------------------------------------------------------------------------- #
def expand_day(
    rng: random.Random, klass: str, persona: dict, day_obj: dict, records: dict,
    recipient_id: str, lifeog_date: dt.date,
) -> dict:
    prof = PROFILE[klass]
    d = day_obj["day"]
    p = d / 60.0
    sleep = day_obj["sleep"]
    activity = day_obj["activity_by_hour"]
    is_event_day = d == 60 and klass in ("응급", "사망")

    # --- 배열 ---
    aix1, aix_h = _expand_aix1(rng, activity, prof["aix1_zero"])
    place = _cat(rng, prof["place"], 1440)
    outgoing = _cat(rng, prof["outgoing"], 1440)  # 거의 254/255 sentinel
    sleep_depth = _expand_sleep_depth(rng, prof, sleep)
    temp, humi, illu = _diurnal(rng, day_obj["env_base"], klass)

    # --- 스칼라: 클래스 분포 + 이벤트 수렴 ---
    if klass == "응급":
        # aix_d: 관측은 ~83% 저값(중앙 33) → 소수 중간(107·127) → 종반 급등(251~323).
        # 130~250 구간은 실측에 거의 없음(저→고 점프).
        if d <= 50:
            aix_d = _clamp(rng.gauss(36, 20), 4, 95)
        elif d <= 54:
            aix_d = _clamp(rng.gauss(115, 14), 90, 150)
        else:
            aix_d = _clamp(rng.gauss(265, 45), 200, 323)
        total_aix_sum = _clamp(rng.gauss(63, 5), 56, 75)
        # night_aix: 관측은 0 소수 + 66~20417 광범위 연속. 종반(D-day 근접)이 최고조.
        if d >= 55:
            night_aix = rng.uniform(9000, 20417)
        else:
            rn = rng.random()
            if rn < 0.15:
                night_aix = rng.uniform(0, 100)
            elif rn < 0.60:
                night_aix = rng.uniform(100, 2231)
            elif rn < 0.80:
                night_aix = rng.uniform(2231, 4460)
            else:
                night_aix = rng.uniform(4460, 9550)
        night_aix = _clamp(night_aix, *prof["night_aix_env"])
        bath_n = len(day_obj["bath_events"])
        bath_count = 0 if bath_n == 0 else round(_clamp(rng.gauss(13, 8), 4, 48))
        out_n = len(day_obj["outgoing_windows"])
        outgoing_count = 0 if out_n == 0 else round(_clamp(rng.gauss(11 * (1 - 0.5 * p), 3), 3, 16))
        total_sleep = _clamp(rng.gauss(141, 120), 0, 719)
    elif klass == "사망":
        aix_d = _clamp(rng.gauss(181, 55), 82, 323)
        # 관측은 163~220 타이트 밀집 + 0 하나 + 278 하나. σ 를 좁혀 군집 재현.
        u_ts = rng.random()
        if u_ts < 0.04:
            total_aix_sum = 0.0
        elif u_ts < 0.95:
            total_aix_sum = _clamp(rng.gauss(180, 13), 160, 215)
        else:
            total_aix_sum = rng.uniform(215, 278)
        night_aix = _clamp(rng.gauss(6, 5), *prof["night_aix_env"])
        bath_count = 0  # ★ 불변
        out_n = len(day_obj["outgoing_windows"])
        outgoing_count = 0 if out_n == 0 else round(_clamp(rng.gauss(6 * (1 - 0.4 * p), 2), 0, 9))
        # 수면 단편화(관측 재현): 정확히 0 인 날 ~40%, 단시간 ~45%, 드물게 장시간 ~15%
        u = rng.random()
        total_sleep = 0.0 if u < 0.40 else (rng.uniform(18, 90) if u < 0.85 else rng.uniform(200, 662))
    else:  # 평시
        aix_d = _clamp(rng.gauss(50, 15), 10, 90)
        total_aix_sum = _clamp(rng.gauss(62, 6), 50, 75)
        night_aix = _clamp(rng.gauss(20, 25), *prof["night_aix_env"])
        bath_count = round(_clamp(rng.gauss(9, 4), 3, 20))
        outgoing_count = round(_clamp(rng.gauss(9, 3), 3, 16))
        total_sleep = _clamp(rng.gauss(400, 60), 280, 520)

    bath_time = round(bath_count * rng.uniform(8, 22), 1) if bath_count else 0.0
    out_time = round(outgoing_count * rng.uniform(20, 100), 1) if outgoing_count else 0.0
    out_late = sum(1 for w in day_obj["outgoing_windows"] if w["start_min"] < 300 or w["start_min"] > 1320)

    row = {
        "source_type": prof["source_type"],
        "care_recipient_id": recipient_id,
        "age": persona["age"], "sex": persona["sex"], "alone": "Y",
        "vision": persona["vision"], "hearing": persona["hearing"], "dosage": persona["dosage"],
        "district": persona["district"], "house_structure": persona["house_structure"],
        "room_no": persona["room_no"], "bath_location": persona["bath_location"],
        "lifeog_date": lifeog_date,
        "emergency_date": lifeog_date if (is_event_day and klass == "응급") else None,
        "emergency_record": records["emergency_record"] if (is_event_day and klass == "응급") else None,
        "occurrence_place": ("욕실" if "욕실" in (records["emergency_record"] or "") else "거실") if (is_event_day and klass == "응급") else None,
        "on_site": "Y" if (is_event_day and klass == "응급") else None,
        "hospital_transfer": "Y" if (is_event_day and klass == "응급") else None,
        "hospital_treatment": "입원" if (is_event_day and klass == "응급") else None,
        "death_date": lifeog_date if (is_event_day and klass == "사망") else None,
        "death_record": records["death_record"] if (is_event_day and klass == "사망") else None,
        # 분단위 배열
        "place_code_1_list": place,
        "aix_1_list": aix1,
        "aix_h_list": aix_h,
        "sleep_depth_1_list": sleep_depth,
        "outgoing_1_list": outgoing,
        # aix 스칼라
        "aix_d": round(aix_d, 1),
        "aix_1_eq_0_repeat_count": _longest_zero_run(aix1),
        "total_aix_sum": round(total_aix_sum, 1),
        "total_aix_inc_ratio": round(rng.uniform(-0.2, 0.4), 3),
        "night_aix_ratio": round(night_aix, 1),
        "total_age_aix_ratio": round(aix_d / max(1, persona["age"]), 3),
        # 수면 (분-int 문자열 — 원본 표기 재현)
        "sleep_start_time_d": str(sleep["start_min"]),
        "sleep_end_time_d": str(sleep["end_min"]),
        "total_sleep_period": round(total_sleep, 1),
        "total_sleep_aix_ratio": round(rng.uniform(0, 0.08), 3),
        # 목욕
        "bath_count_d": bath_count,
        "bath_time_d": bath_time,
        "bath_nomove_time": round(rng.uniform(0, 20), 1) if bath_count else 0.0,
        "bath_count_in_sleep": 0,
        "bath_time_per_count": round(bath_time / bath_count, 1) if bath_count else 0.0,
        "total_bath_average_count": round(rng.uniform(4, 14), 1) if bath_count else 0.0,
        # 외출
        "outgoing_count_d": outgoing_count,
        "outgoing_time_d": out_time,
        "outgoing_late_night_count_d": out_late,
        "outgoing_late_night_time_d": round(out_late * rng.uniform(10, 40), 1),
        "last_outgoing_time": (
            f"{day_obj['outgoing_windows'][-1]['end_min'] // 60:02d}:{day_obj['outgoing_windows'][-1]['end_min'] % 60:02d}"
            if day_obj["outgoing_windows"] else None
        ),
        "total_outgoing_average_time": round(rng.uniform(100, 200), 1) if outgoing_count else 0.0,
        "total_outgoing_average_count": round(rng.uniform(3, 12), 1) if outgoing_count else 0.0,
        # 환경
        "temp_list": temp, "humi_list": humi, "illu_list": illu,
    }
    _validate_row(klass, row)
    return row


def expand_person(gen_obj: dict, recipient_id: str, start_date: dt.date, seed: int) -> list[dict]:
    klass = gen_obj["class"]
    rng = random.Random(f"exp-{recipient_id}-{seed}")
    rows = []
    for day_obj in gen_obj["daily"]:
        lifeog = start_date + dt.timedelta(days=day_obj["day"] - 1)
        rows.append(expand_day(rng, klass, gen_obj["persona"], day_obj, gen_obj["records"], recipient_id, lifeog))
    return rows


# --------------------------------------------------------------------------- #
# 행 불변값 검증
# --------------------------------------------------------------------------- #
def _validate_row(klass: str, r: dict) -> None:
    assert len(r["aix_1_list"]) == 1440 and len(r["place_code_1_list"]) == 1440
    assert len(r["outgoing_1_list"]) == 1440 and len(r["aix_h_list"]) == 24
    assert len(r["temp_list"]) == 24 and len(r["humi_list"]) == 24 and len(r["illu_list"]) == 24
    assert all(x == 0 or x in AIX_LEVELS for x in r["aix_1_list"]), "aix_1 비제로는 관측 레벨집합만"
    if r["sleep_depth_1_list"] is not None:
        assert all(0 <= x <= 4 for x in r["sleep_depth_1_list"]), "sleep_depth 0~4"
    lo, hi = PROFILE[klass]["night_aix_env"]
    assert lo <= r["night_aix_ratio"] <= hi, f"night_aix 봉투 위반 {r['night_aix_ratio']}"
    assert set(r["outgoing_1_list"]) <= {0, 254, 255}, "outgoing sentinel 도메인"
    if klass == "사망":
        assert r["bath_count_d"] == 0 and r["bath_time_d"] == 0.0, "사망 목욕 0 불변"
        assert r["sleep_depth_1_list"] is None, "사망 sleep_depth 결측"
