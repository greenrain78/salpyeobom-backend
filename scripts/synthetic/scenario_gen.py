"""ADL 합성데이터 시나리오 생성기 — 독거노인 60일.

`/goal` 계약(persona·scenario·daily[60]·records)을 만족하는 JSON 을 생성한다.
정량 분포는 adl_raw_records id 1~60(응급 1명·사망 1명, 각 30일)에서 도출한 값에만
근거한다. 1440 분단위 배열과 스칼라 지표는 이 산출물을 받는 후속 익스팬더가
전개하므로 여기서는 다루지 않는다.

근거 분포 (id 1~60 프로파일):
  응급(id1~30): bath_count 4~48(avg13), outgoing_count 3~16(avg10),
    total_sleep 0~719(avg141), aix_d 4~323(avg64), night_aix 0~20417(avg3584, 大),
    temp 21.9~32.8, humi 53~71.5, illu_peak 0~71
  사망(id31~60): bath_count 0(불변), outgoing_count 0~9(avg5),
    total_sleep 0~662(avg83), aix_d 82~312(avg181), night_aix 0~15(avg6, 小),
    temp 23.3~28.6, humi 42.3~71.7, illu_peak 0~125
  평시: id1~60 에 라벨 없음 → 이벤트에서 먼 안정 구간을 기저로 외삽.

실행:
  uv run python scripts/synthetic/scenario_gen.py            # 클래스별 1명씩 샘플
  uv run python scripts/synthetic/scenario_gen.py 응급 7     # 특정 클래스·시드 1건
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

Klass = str  # "평시" | "응급" | "사망"

OUT_DIR = Path(__file__).resolve().parents[2] / "out" / "synthetic"


# --------------------------------------------------------------------------- #
# 페르소나 풀 (관측 페르소나를 중심으로 시드 다양화)
# --------------------------------------------------------------------------- #
_DOSAGE = ["없음", "고혈압", "당뇨", "고혈압+당뇨", "관절염약", "심장약"]
_VH = ["양호", "보통", "나쁨"]


def _persona(rng: random.Random, klass: Klass) -> dict[str, Any]:
    if klass == "평시":
        age = rng.randint(72, 84)
        base_activity = rng.choice(["mid", "mid", "high"])
        dosage = rng.choice(["없음", "고혈압", "당뇨", "고혈압+당뇨"])
    elif klass == "응급":
        age = rng.randint(75, 88)
        base_activity = rng.choice(["mid", "mid", "low"])
        dosage = rng.choice(["고혈압", "관절염약", "고혈압+당뇨", "심장약"])
    else:  # 사망
        age = rng.randint(80, 93)
        base_activity = "low"
        dosage = rng.choice(["고혈압", "당뇨", "심장약", "고혈압+당뇨"])

    return {
        "age": age,
        "sex": rng.choice(["M", "F"]),
        "alone": "Y",  # 전원 독거
        "vision": rng.choice(["양호", "보통", "보통", "나쁨"]),
        "hearing": rng.choice(["양호", "보통", "보통", "나쁨"]),
        "dosage": dosage,
        "district": rng.choice(["도시", "농촌"]) if klass != "사망" else rng.choice(["농촌", "농촌", "도시"]),
        "house_structure": rng.choice(["주택", "아파트"]),
        "room_no": rng.randint(1, 3),
        "bath_location": "옥내",  # 관측 전부 옥내
        "base_activity": base_activity,
    }


# --------------------------------------------------------------------------- #
# 서사 동인 풀
# --------------------------------------------------------------------------- #
_PYEONGSI_LIFE = [
    ("텃밭", "마당 텃밭을 가꾸며 아침저녁으로 물을 주고, 주말엔 딸이 다녀간다"),
    ("경로당", "동네 경로당 단골로 점심을 함께 들고 화투를 친다"),
    ("신앙", "주 3회 새벽 예배에 나가고 교우들과 점심 모임을 갖는다"),
    ("손주", "낮 동안 손주를 잠깐 돌봐주고 저녁이면 혼자 드라마를 본다"),
    ("산책", "강변 산책 동호회에서 매일 아침 한 시간씩 걷는다"),
]
_EMG_ARC = [
    ("관절염", "무릎 관절염", "거동이 점점 줄고", "화장실을 가다 욕실에서 미끄러져 넘어졌다"),
    ("어지럼", "기립성 저혈압", "어지럼이 잦아지고", "거실에서 일어서다 정신을 잃고 쓰러졌다"),
    ("감기", "독감 합병증", "기침과 미열로 수면이 무너지고", "탈수와 기력 저하로 주저앉아 일어나지 못했다"),
    ("심장", "심방세동", "가슴 두근거림과 호흡곤란이 심해지고", "흉통으로 의식이 흐려졌다"),
]
_DTH_ARC = [
    ("노환", "노환에 따른 전신 쇠약", "끼니를 거르는 날이 늘고 자리보전이 길어졌다"),
    ("만성", "만성질환 악화", "복약을 거르며 부종과 호흡곤란이 깊어졌다"),
    ("영양", "식욕 상실과 영양실조", "물조차 넘기기 어려워지며 누워 지내는 시간이 늘었다"),
    ("폐렴", "흡인성 폐렴", "기침과 미열 끝에 의식이 흐려지며 반응이 사라졌다"),
]
_HOSPITALS = ["세일병원", "중앙의료원", "성모병원", "시립병원", "한사랑병원"]


# --------------------------------------------------------------------------- #
# 하루 일과표 빌더
# --------------------------------------------------------------------------- #
def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _activity_day(rng: random.Random, day_mean: float, night_level: float) -> list[int]:
    """24시간 활동 강도(0~3). 0~5시는 night_level, 주간은 day_mean 중심."""
    hours: list[int] = []
    for h in range(24):
        if 0 <= h < 6:  # 야간
            base = night_level
        elif h in (6, 7, 8, 12, 13, 18, 19):  # 식사·기상·취침 전후 피크
            base = day_mean + 0.7
        elif 9 <= h <= 21:  # 주간
            base = day_mean
        else:  # 22~23시 취침 준비
            base = day_mean * 0.4
        lvl = round(_clamp(base + rng.uniform(-0.5, 0.5), 0, 3))
        hours.append(int(lvl))
    return hours


def _sleep_window(rng: random.Random, bed_center: int, wake_center: int, jitter: int) -> dict[str, int]:
    start = int(_clamp(bed_center + rng.randint(-jitter, jitter), 0, 1439))
    end = int(_clamp(wake_center + rng.randint(-jitter, jitter), 0, 1439))
    return {"start_min": start, "end_min": end}


def _bath_events(rng: random.Random, count: int) -> list[dict[str, int]]:
    """옥내 욕실 출입 이벤트(목욕 센서). 사망 클래스는 호출하지 않는다."""
    events = []
    used: set[int] = set()
    for _ in range(count):
        h = rng.choice([7, 8, 9, 11, 14, 17, 19, 20, 21])
        if h in used:
            continue
        used.add(h)
        events.append({"hour": h, "dur_min": rng.randint(5, 35)})
    return sorted(events, key=lambda e: e["hour"])


def _outgoing_windows(rng: random.Random, count: int) -> list[dict[str, int]]:
    windows = []
    starts = sorted(rng.sample(range(7 * 60, 19 * 60), max(0, count)))
    for s in starts:
        dur = rng.randint(20, 130)
        windows.append({"start_min": s, "end_min": int(_clamp(s + dur, 0, 1439))})
    return windows


def _env(rng: random.Random, day: int, klass: Klass) -> dict[str, float]:
    """여름철 60일 환경 기저. 클래스별 관측 범위 안에서 완만한 계절 추세 + 일변동."""
    season = 1.5 * (day / 60.0)  # 초여름→한여름 완만 상승
    if klass == "사망":
        temp = _clamp(25.0 + season + rng.uniform(-1.3, 1.3), 23.3, 28.6)
        humi = _clamp(60.0 + rng.uniform(-15, 11), 42.3, 71.7)
        illu = _clamp(rng.choice([0, 8, 20, 45, 70, 95, 125]) + rng.uniform(-10, 10), 0, 125)
    else:  # 평시·응급
        temp = _clamp(26.5 + season + rng.uniform(-1.8, 2.0), 22.0, 32.8)
        humi = _clamp(63.0 + rng.uniform(-9, 8), 50.0, 71.5)
        illu = _clamp(rng.choice([0, 5, 15, 35, 55, 71]) + rng.uniform(-5, 8), 0, 90)
    return {"temp": round(temp, 1), "humi": round(humi, 1), "illu_peak": round(illu, 1)}


# --------------------------------------------------------------------------- #
# 클래스별 60일 전개
# --------------------------------------------------------------------------- #
_BASE_LEVEL = {"low": 1.0, "mid": 1.6, "high": 2.1}


def _daily_pyeongsi(rng: random.Random, persona: dict) -> list[dict]:
    base = _BASE_LEVEL[persona["base_activity"]]
    days = []
    for d in range(1, 61):
        weekly = 0.25 * (1 if d % 7 in (5, 6, 0) else 0)  # 주말 약간 활발
        day_mean = base + weekly + rng.uniform(-0.2, 0.2)
        days.append(
            {
                "day": d,
                "sleep": _sleep_window(rng, 1365, 405, 35),  # ~22:45 취침, ~06:45 기상
                "activity_by_hour": _activity_day(rng, day_mean, night_level=0.1),
                "bath_events": _bath_events(rng, rng.choice([1, 2, 2, 3])),
                "outgoing_windows": _outgoing_windows(rng, rng.choice([1, 2, 2, 3])),
                "env_base": _env(rng, d, "평시"),
            }
        )
    return days


def _daily_emergency(rng: random.Random, persona: dict) -> list[dict]:
    base = _BASE_LEVEL[persona["base_activity"]]
    days = []
    for d in range(1, 61):
        p = d / 60.0
        # 거동 점진 저하: 후반으로 갈수록 주간 활동 감소
        day_mean = base * (1.0 - 0.40 * p) + rng.uniform(-0.2, 0.2)
        # 야간 불안정: 마지막 ~12일 급등(night_aix 大 시그니처)
        night = 0.1
        if d >= 49:
            night = 0.1 + 1.7 * ((d - 48) / 12.0)
        # 외출 점감
        out_n = max(0, round(3 * (1.0 - 0.7 * p)))
        bath_n = rng.choice([1, 2, 2, 3]) if d < 58 else rng.choice([0, 1])

        day = {
            "day": d,
            "sleep": _sleep_window(rng, 1365, 405, 40),
            "activity_by_hour": _activity_day(rng, day_mean, night_level=night),
            "bath_events": _bath_events(rng, bath_n),
            "outgoing_windows": _outgoing_windows(rng, out_n),
            "env_base": _env(rng, d, "응급"),
        }
        if d == 60:  # 응급 당일: 새벽 욕실 사건 → 활동 교란 후 소멸
            act = [0] * 24
            act[4] = 3  # 새벽 사건 스파이크
            act[5] = 2
            for h in range(6, 12):
                act[h] = 1  # 구급·이송으로 부분 활동
            day["activity_by_hour"] = act
            day["sleep"] = {"start_min": 1380, "end_min": 270}  # 짧고 교란된 수면
            day["bath_events"] = [{"hour": 4, "dur_min": 12}]
            day["outgoing_windows"] = []
        days.append(day)
    return days


def _daily_death(rng: random.Random, persona: dict) -> list[dict]:
    base = _BASE_LEVEL[persona["base_activity"]]
    days = []
    for d in range(1, 61):
        p = d / 60.0
        # 말기 쇠약: 주간 활동이 0 으로 붕괴
        day_mean = base * (1.0 - 0.85 * p) + rng.uniform(-0.15, 0.15)
        day_mean = max(0.0, day_mean)
        # 외출은 점차 뜸해지나 말기까지 완전히 끊기진 않는다(실측 outgoing_count avg 5)
        out_n = max(0, round(3 * (1.0 - 0.7 * p)))
        # 수면 단편화: 주간에도 누워 지내나 구조적 수면은 짧음
        day = {
            "day": d,
            "sleep": _sleep_window(rng, 1350, 360, 70),  # 불규칙·단편적
            "activity_by_hour": _activity_day(rng, day_mean, night_level=0.05),
            "bath_events": [],  # 사망 클래스 불변: 목욕 0
            "outgoing_windows": _outgoing_windows(rng, out_n),
            "env_base": _env(rng, d, "사망"),
        }
        if d == 60:  # 사망 당일: 활동 소멸
            day["activity_by_hour"] = [0] * 24
            day["sleep"] = {"start_min": 1320, "end_min": 600}
            day["outgoing_windows"] = []
        days.append(day)
    return days


# --------------------------------------------------------------------------- #
# 서사·기록 텍스트
# --------------------------------------------------------------------------- #
def _scenario_and_records(rng: random.Random, klass: Klass, persona: dict) -> tuple[str, dict]:
    age, sex = persona["age"], "할머니" if persona["sex"] == "F" else "할아버지"
    loc = persona["district"]
    if klass == "평시":
        _, life = rng.choice(_PYEONGSI_LIFE)
        scenario = (
            f"{loc}에서 혼자 사는 {age}세 {sex}. {life}. "
            f"복약과 식사 리듬이 규칙적이고 이웃과의 왕래도 꾸준해, 60일 내내 수면·활동·"
            f"외출이 기저선 주변에서 안정적으로 변동한다. 별다른 이벤트 없이 평온한 일상이 이어진다."
        )
        return scenario, {"emergency_record": None, "death_record": None}

    if klass == "응급":
        _, cond, trend, fall = rng.choice(_EMG_ARC)
        hosp = rng.choice(_HOSPITALS)
        scenario = (
            f"{loc}에서 혼자 사는 {age}세 {sex}. 평소 {persona['dosage']} 약을 복용하며 지내던 중 "
            f"{cond}이 D-50 무렵부터 악화되어 {trend} 외출이 줄었다. D-7부터 수면이 무너지고 "
            f"야간에 화장실을 자주 오가며 불안정해졌다. 60일째 새벽 {fall}."
        )
        emg = (
            f"06:40 G/W 무신호 / 새벽 {fall}. "
            f"07:10 미응답 2회 → 이웃 신고, 119 출동. "
            f"07:35 {hosp} 이송, 응급 처치 후 입원."
        )
        return scenario, {"emergency_record": emg, "death_record": None}

    # 사망
    _, cause, decline = rng.choice(_DTH_ARC)
    scenario = (
        f"{loc}에서 혼자 사는 {age}세 {sex}. {persona['dosage']} 복용 중 {cause}로 기력이 쇠해 갔다. "
        f"{decline}. 외출이 점차 뜸해지고, 목욕은 60일 내내 한 번도 관측되지 않는다. "
        f"활동과 수면이 점차 소멸하며 60일째 사망에 이른다."
    )
    dth = f"노환 및 {cause}로 인한 사망. 무동작 지속·활동 소멸 후 발견."
    return scenario, {"emergency_record": None, "death_record": dth}


# --------------------------------------------------------------------------- #
# 조립 + 검증
# --------------------------------------------------------------------------- #
def generate(klass: Klass, seed: int) -> dict[str, Any]:
    rng = random.Random(f"{klass}-{seed}")
    persona = _persona(rng, klass)
    scenario, records = _scenario_and_records(rng, klass, persona)
    daily = {
        "평시": _daily_pyeongsi,
        "응급": _daily_emergency,
        "사망": _daily_death,
    }[klass](rng, persona)
    obj = {"class": klass, "persona": persona, "scenario": scenario, "daily": daily, "records": records}
    validate(obj)
    return obj


def validate(obj: dict) -> None:
    """계약·클래스 불변값 강제. 위반 시 예외."""
    klass = obj["class"]
    assert klass in ("평시", "응급", "사망"), klass
    assert obj["persona"]["alone"] == "Y"
    assert 70 <= obj["persona"]["age"] <= 95
    daily = obj["daily"]
    assert len(daily) == 60, f"daily must be 60, got {len(daily)}"
    for i, d in enumerate(daily, 1):
        assert d["day"] == i, f"day index {d['day']} != {i}"
        a = d["activity_by_hour"]
        assert len(a) == 24 and all(isinstance(x, int) and 0 <= x <= 3 for x in a), f"day{i} activity"
        assert 0 <= d["sleep"]["start_min"] <= 1439 and 0 <= d["sleep"]["end_min"] <= 1439
        for b in d["bath_events"]:
            assert 0 <= b["hour"] <= 23 and b["dur_min"] >= 0
        for w in d["outgoing_windows"]:
            assert 0 <= w["start_min"] <= 1439 and 0 <= w["end_min"] <= 1439
        e = d["env_base"]
        assert 22 <= e["temp"] <= 33 and 42 <= e["humi"] <= 72 and 0 <= e["illu_peak"] <= 125, f"day{i} env"
    # 클래스 불변값
    if klass == "사망":
        assert all(d["bath_events"] == [] for d in daily), "사망 클래스는 목욕 0 (bath_events 항상 [])"
        assert obj["records"]["death_record"] and obj["records"]["emergency_record"] is None
    elif klass == "응급":
        assert obj["records"]["emergency_record"] and obj["records"]["death_record"] is None
    else:
        assert obj["records"] == {"emergency_record": None, "death_record": None}


def _summary(obj: dict) -> str:
    daily = obj["daily"]

    def day_act(d):
        return sum(d["activity_by_hour"])

    def night_act(d):
        return sum(d["activity_by_hour"][0:6])

    first, last = daily[0], daily[59]
    return (
        f"  주간활동합 day1={day_act(first):>2} → day60={day_act(last):>2} | "
        f"야간활동 day1={night_act(first)} → day55={night_act(daily[54])} → day60={night_act(last)} | "
        f"외출 day1={len(first['outgoing_windows'])}→day60={len(last['outgoing_windows'])} | "
        f"목욕일수={sum(1 for d in daily if d['bath_events'])}/60"
    )


def main(argv: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if len(argv) >= 2:
        jobs = [(argv[0], int(argv[1]))]
    else:
        jobs = [("평시", 1), ("응급", 2), ("사망", 3)]
    for klass, seed in jobs:
        obj = generate(klass, seed)
        path = OUT_DIR / f"{klass}_seed{seed}.json"
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        p = obj["persona"]
        print(f"[{klass} seed={seed}] {p['age']}세 {p['sex']} {p['dosage']} {p['district']} "
              f"base={p['base_activity']} → {path.relative_to(OUT_DIR.parents[1])}")
        print(f"  서사: {obj['scenario'][:90]}…")
        print(_summary(obj))
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
