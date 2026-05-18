"""가상 ADL 데이터 생성 스크립트 (실측 샘플 기반)

실측 기준:
  - 응급: 05-1 ...응급상황 발생 ADL... 1명 30일 (AIX 점진 감소)
  - 사망: 05-2 ...사망 발생 ADL...     1명 30일 (bath_count=0 전체)
  - 정상: 응급 환자 30일 전 패턴에서 추론

사용법:
  uv run python scripts/seed_adl.py          # 없는 환자만 추가
  uv run python scripts/seed_adl.py --reset  # NOR/EMR/DTH 전체 재생성
"""
import asyncio
import random
import sys
from datetime import date, datetime, timedelta, timezone

from tortoise import Tortoise

sys.path.insert(0, ".")
from app.database import TORTOISE_ORM
from app.models.adl import AdlDailyRecord, AdlHourlyEnvironment
from app.models.patient import Patient, Situation, TimeseriesData

# ── 날짜 범위: 29일 전 ~ 오늘 ─────────────────────────────────────
TODAY = date.today()
DATES = [TODAY - timedelta(days=29 - i) for i in range(30)]

# ── 시간별 조도 기준값 (실측 2개 파일 평균) ────────────────────────
ILLU_BASE = [0, 0, 0, 0, 1, 2, 2, 6, 12, 18, 25, 27, 28, 28, 27, 23, 17, 9, 5, 4, 2, 1, 0, 0]

# ── 환자 메타 풀 ─────────────────────────────────────────────────
_MALE = ["김철수", "이영호", "박민준", "정대웅", "최성철", "한상훈", "조병철", "임영수",
         "강동원", "서진우", "윤기현", "장성민", "오재석", "권혁준", "안재호",
         "송민기", "유성준", "나태환", "남기웅", "배재환", "백성식", "전종명",
         "허재현", "진성수", "원희태", "신재호", "양성준", "변기철", "심재운", "우종철"]
_FEMALE = ["김순자", "이영희", "박미숙", "정현숙", "최경자", "한순례", "조미희", "임영자",
           "강미선", "서정숙", "윤말순", "장순희", "오명자", "권순례", "안미자",
           "송점숙", "유순희", "나현숙", "남순이", "배정자", "백미순", "전정자",
           "허순임", "진미순", "원정자", "신미숙", "양영숙", "변순례", "심미자", "우점순"]
_DISTRICTS = [
    "서울 노원구 상계동", "서울 노원구 중계동", "서울 강북구 수유동",
    "서울 도봉구 쌍문동", "서울 은평구 불광동", "서울 성북구 길음동",
    "서울 강서구 화곡동", "서울 관악구 봉천동", "서울 양천구 신월동",
    "부산 수영구 광안동", "부산 동래구 명륜동", "부산 북구 화명동",
    "인천 남동구 구월동", "인천 계양구 작전동", "대구 달서구 성당동",
    "경기 수원 팔달구", "경기 성남 분당구", "경기 고양 일산동구",
    "경기 용인 기흥구", "대전 유성구 노은동",
]
_MANAGERS = ["김재섭 주무관", "이수진 주무관", "박민준 주무관", "최영철 주무관", "정하나 주무관"]
_NOR_DISEASES = [
    ["고혈압"], ["당뇨"], ["관절염"], ["골다공증", "고혈압"],
    ["고지혈증", "관절염"], ["고혈압", "당뇨"], ["골다공증"],
]
_EMR_DISEASES = [
    ["고혈압", "당뇨"], ["심부전"], ["초기 치매", "고혈압"],
    ["뇌졸중", "고혈압"], ["관절염", "당뇨"], ["고혈압", "심부전"],
]
_DTH_DISEASES = [
    ["심부전", "당뇨"], ["중기 치매", "고혈압", "신부전"],
    ["뇌졸중", "암"], ["폐렴", "심부전"],
    ["중기 치매", "고혈압"], ["말기 암", "고혈압"],
]


# ── 헬퍼 ────────────────────────────────────────────────────────

def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _gauss(mu: float, sigma: float, lo: float, hi: float) -> float:
    return _clip(random.gauss(mu, sigma), lo, hi)


def _fmt(h: int, m: int) -> str:
    return f"{h:02d}:{m:02d}"


# ── 환자 프로필 정의 ──────────────────────────────────────────────

def _make_profiles() -> list[dict]:
    rng = random.Random(777)
    profiles = []
    groups = [
        ("NOR", 30, (65, 84), _NOR_DISEASES, 3.0,
         ["자립 관리군 (3등급)", "일반 관리군 (2등급)"]),
        ("EMR", 30, (70, 89), _EMR_DISEASES, 2.5,
         ["일반 관리군 (2등급)", "집중 관리군 (1등급)"]),
        ("DTH", 30, (78, 95), _DTH_DISEASES, 2.2,
         ["집중 관리군 (1등급)"]),
    ]
    for group, count, age_range, diseases_pool, threshold, mgmt_pool in groups:
        for i in range(1, count + 1):
            pid = f"{group}_{i:03d}"
            sex = rng.choice(["M", "F"])
            name = (_MALE if sex == "M" else _FEMALE)[(i - 1) % 30]
            age = rng.randint(*age_range)
            district = _DISTRICTS[(i - 1) % len(_DISTRICTS)]
            house_no = rng.randint(1, 999)
            profiles.append({
                "group": group,
                "patient_id": pid,
                "name": name,
                "age": age,
                "address_full": f"{district} {house_no}번지",
                "address_summary": f"{district.split()[-1]} {house_no}번지",
                "doc_no": f"NO.2026-ADL-{group}-{i:03d}",
                "phone_number": f"010-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
                "threshold_value": threshold,
                "manager_name": _MANAGERS[(i - 1) % len(_MANAGERS)],
                "management_level": rng.choice(mgmt_pool),
                "diseases": list(rng.choice(diseases_pool)),
                "track_A_state": "정상" if group == "NOR" else "응급",
                "track_B_anomaly": "정상" if group == "NOR" else "비정상",
                "cross_verification_level": "정상" if group == "NOR" else "초고위험",
                "alert_title": (
                    None if group == "NOR" else "이상 패턴 감지"
                ),
                "alert_desc": (
                    None if group == "NOR"
                    else "AI 이상 탐지: 활동지수 급감 및 응급 패턴 감지" if group == "EMR"
                    else "AI 이상 탐지: 욕실 미감지 및 활동 소실 패턴"
                ),
            })
    return profiles


# ── 시간별 환경 데이터 ────────────────────────────────────────────

def _gen_hourly_env(day_idx: int) -> list[dict]:
    # 실측 온도 26~28°C, 습도 59~65%, 조도 0~41 lux
    base_temp = 26.5 + (day_idx / 29) * 1.5
    base_humi = 63.0 - (day_idx / 29) * 3.0
    rows = []
    for h in range(24):
        illu_raw = ILLU_BASE[h] * random.uniform(0.6, 1.4) + random.uniform(-0.5, 0.5)
        temp_adj = 0.5 if 9 <= h <= 17 else -0.3
        rows.append({
            "hour": h,
            "temperature": round(_gauss(base_temp + temp_adj, 0.4, 22.0, 33.0), 1),
            "humidity": round(_gauss(base_humi + (1.5 if 5 <= h <= 9 else 0), 1.5, 44.0, 78.0), 1),
            "illuminance": round(_clip(illu_raw, 0.0, 60.0), 1),
        })
    return rows


# ── 그룹별 일별 ADL 생성 ─────────────────────────────────────────

def _gen_normal_day(_day_idx: int) -> dict:
    aix = _gauss(250, 50, 150, 380)
    bath = random.randint(4, 10)
    bath_time = bath * random.uniform(8, 20)
    out = random.randint(2, 8)
    ss_h, ss_m = random.randint(21, 22), random.choice([0, 15, 30, 45])
    se_h, se_m = random.randint(5, 7), random.choice([0, 15, 30, 45])
    return {
        "aix_score": round(aix, 1),
        "total_sleep_period": round(_gauss(420, 60, 300, 540), 1),
        "total_sleep_aix_ratio": round(random.uniform(0.01, 0.08), 3),
        "sleep_start_time": _fmt(ss_h, ss_m),
        "sleep_end_time": _fmt(se_h, se_m),
        "bath_count": bath,
        "bath_time": round(bath_time, 1),
        "bath_nomove_time": round(bath_time * random.uniform(0.05, 0.2), 1),
        "bath_count_in_sleep": random.choices([0, 1], weights=[80, 20])[0],
        "outgoing_count": out,
        "outgoing_time": round(out * random.uniform(20, 60), 1),
        "outgoing_late_night_count": random.choices([0, 1], weights=[95, 5])[0],
        "outgoing_late_night_time": 0.0,
    }


def _gen_emergency_day(day_idx: int) -> dict:
    """day_idx 0=29일 전(정상 수준), 29=응급 발생일"""
    if day_idx < 10:
        aix = _gauss(250, 50, 180, 320)
        bath = random.randint(8, 20)
        sleep_p = random.uniform(0, 720)
    elif day_idx < 20:
        aix = _gauss(150, 40, 100, 200)
        bath = random.randint(6, 16)
        sleep_p = random.uniform(0, 720)
    elif day_idx < 28:
        aix = _gauss(65, 25, 30, 100)
        bath = random.randint(4, 12)
        sleep_p = random.uniform(0, 600)
    else:
        aix = _gauss(20, 12, 4, 40)
        bath = random.randint(4, 10)
        sleep_p = random.uniform(0, 200)

    out = max(0, random.randint(3, 16) if day_idx < 20 else random.randint(0, 8))
    late_time = round(_gauss(97, 102, 0, 240), 1)
    bath_time = bath * random.uniform(5, 18)
    ss_h = random.randint(0, 23)
    se_h = random.randint(0, 23)
    return {
        "aix_score": round(aix, 1),
        "total_sleep_period": round(sleep_p, 1),
        "total_sleep_aix_ratio": round(random.uniform(0.01, 0.12), 3),
        "sleep_start_time": _fmt(ss_h, random.choice([0, 15, 30, 45])),
        "sleep_end_time": _fmt(se_h, random.choice([0, 15, 30, 45])),
        "bath_count": bath,
        "bath_time": round(bath_time, 1),
        "bath_nomove_time": round(random.uniform(1, 30), 1),
        "bath_count_in_sleep": random.choices([0, 1], weights=[70, 30])[0],
        "outgoing_count": out,
        "outgoing_time": round(out * random.uniform(15, 70), 1) if out else 0.0,
        "outgoing_late_night_count": 1 if late_time > 0 else 0,
        "outgoing_late_night_time": late_time,
    }


def _gen_death_day(_day_idx: int) -> dict:
    """사망 그룹: bath=0, 수면 대부분 미감지 (실측 기반)"""
    aix = _gauss(180, 55, 82, 320)
    out = random.randint(0, 9)
    late_time = round(_gauss(7.5, 13, 0, 45), 1)
    sleep_p = 0.0 if random.random() < 0.90 else round(random.uniform(20, 660), 1)
    return {
        "aix_score": round(aix, 1),
        "total_sleep_period": sleep_p,
        "total_sleep_aix_ratio": round(random.uniform(0.0, 0.05), 3),
        "sleep_start_time": None,
        "sleep_end_time": None,
        "bath_count": 0,
        "bath_time": 0.0,
        "bath_nomove_time": 0.0,
        "bath_count_in_sleep": 0,
        "outgoing_count": out,
        "outgoing_time": round(out * random.uniform(10, 50), 1) if out else 0.0,
        "outgoing_late_night_count": 1 if late_time > 0 else 0,
        "outgoing_late_night_time": late_time,
    }


_DAY_GEN = {"NOR": _gen_normal_day, "EMR": _gen_emergency_day, "DTH": _gen_death_day}


# ── MAE 스코어 ────────────────────────────────────────────────────

def _gen_mae(group: str, day_idx: int, threshold: float) -> tuple[float, bool]:
    if group == "NOR":
        mae = threshold * random.uniform(0.25, 0.72)
        return round(mae, 3), False
    if group == "EMR":
        if day_idx < 20:
            mae = threshold * random.uniform(0.60, 0.93)
            return round(mae, 3), False
        if day_idx < 28:
            mae = threshold * random.uniform(1.05, 1.70)
            return round(mae, 3), True
        mae = threshold * random.uniform(1.80, 2.50)
        return round(mae, 3), True
    # DTH
    if day_idx < 10:
        mae = threshold * random.uniform(0.90, 1.10)
        return round(mae, 3), mae > threshold
    if day_idx < 20:
        mae = threshold * random.uniform(1.10, 1.60)
        return round(mae, 3), True
    mae = threshold * random.uniform(1.60, 3.00)
    return round(mae, 3), True


# ── 메인 시드 함수 ────────────────────────────────────────────────

async def seed(reset: bool = False) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

    profiles = _make_profiles()
    target_ids = [p["patient_id"] for p in profiles]

    if reset:
        await TimeseriesData.filter(patient_id__in=target_ids).delete()
        await Situation.filter(patient_id__in=target_ids).delete()
        # AdlDailyRecord → AdlHourlyEnvironment (CASCADE)
        patients_to_reset = await Patient.filter(patient_id__in=target_ids)
        for p in patients_to_reset:
            await AdlDailyRecord.filter(patient=p).delete()
        await Patient.filter(patient_id__in=target_ids).delete()
        print("기존 ADL 데이터 삭제 완료")

    cnt_p = cnt_adl = cnt_env = cnt_ts = cnt_sit = 0

    for prof in profiles:
        group = prof["group"]
        threshold = prof["threshold_value"]
        patient_data = {k: v for k, v in prof.items() if k != "group"}

        random.seed(hash(prof["patient_id"]) & 0x7FFFFFFF)

        patient, created = await Patient.get_or_create(
            patient_id=prof["patient_id"],
            defaults=patient_data,
        )
        if created:
            cnt_p += 1

        gen_day = _DAY_GEN[group]
        bath_sum = 0

        for day_idx, record_date in enumerate(DATES):
            adl = gen_day(day_idx)

            # 누적 목욕 횟수 평균
            bath_sum += adl["bath_count"]
            adl["total_bath_average_count"] = round(bath_sum / (day_idx + 1), 2)

            mae, is_anomaly = _gen_mae(group, day_idx, threshold)

            dr, dr_created = await AdlDailyRecord.get_or_create(
                patient=patient,
                record_date=record_date,
                defaults={**adl, "mae_score": mae, "is_anomaly": is_anomaly},
            )
            if dr_created:
                cnt_adl += 1
                env_objs = [
                    AdlHourlyEnvironment(daily_record=dr, **h)
                    for h in _gen_hourly_env(day_idx)
                ]
                await AdlHourlyEnvironment.bulk_create(env_objs, ignore_conflicts=True)
                cnt_env += 24

            _, ts_created = await TimeseriesData.get_or_create(
                patient=patient,
                date=record_date,
                defaults={"mae_score": mae, "is_anomaly": is_anomaly},
            )
            if ts_created:
                cnt_ts += 1

        # 응급/사망 상황 생성 (마지막 날)
        if group in ("EMR", "DTH"):
            occurred_at = datetime.combine(DATES[-1], datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            _, sit_created = await Situation.get_or_create(
                patient=patient,
                occurred_at=occurred_at,
                defaults={
                    "category": "이상 패턴" if group == "EMR" else "사망 감지",
                    "detail_reason": (
                        "AI 이상 탐지: 활동지수 급감 및 응급 패턴 감지"
                        if group == "EMR"
                        else "AI 이상 탐지: 욕실 미감지 및 활동 소실 패턴"
                    ),
                    "action_status": "현장 출동" if group == "EMR" else "조치 완료",
                    "is_active": group == "EMR",
                },
            )
            if sit_created:
                cnt_sit += 1

    print(f"환자: {cnt_p}명 생성 (총 {await Patient.all().count()}명)")
    print(f"ADL 일별: {cnt_adl}건 생성 (총 {await AdlDailyRecord.all().count()}건)")
    print(f"ADL 시간별: {cnt_env}건 생성 (총 {await AdlHourlyEnvironment.all().count()}건)")
    print(f"시계열: {cnt_ts}개 생성 (총 {await TimeseriesData.all().count()}개)")
    print(f"상황: {cnt_sit}건 생성 (총 {await Situation.all().count()}건)")
    print("시드 완료")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed(reset="--reset" in sys.argv))
