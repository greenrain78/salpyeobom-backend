"""엑셀 샘플 ADL 원시 데이터 → DB 적재 스크립트

사용법:
  uv run python scripts/seed_adl_raw.py          # 없는 행만 추가
  uv run python scripts/seed_adl_raw.py --reset  # 전체 삭제 후 재생성
"""

import asyncio
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from tortoise import Tortoise

sys.path.insert(0, ".")
from app.database import TORTOISE_ORM
from app.models.adl_raw import AdlRawRecord

SAMPLE_DIR = Path(__file__).parent.parent / "sample"
EMERGENCY_FILE = SAMPLE_DIR / "05-1 데이터바우처 지원사업 데이터 샘플(응급상황 발생 ADL)_리본케어.xlsx"
DEATH_FILE = SAMPLE_DIR / "05-2 데이터바우처 지원사업 데이터 샘플(사망 발생 ADL)_리본케어.xlsx"

_LIST_COLS = {"place_code_1_list", "AIX_1_list", "sleep_depth_1_list", "outgoing_1_list"}
_DATE_COLS_EMERGENCY = {"lifeog_date", "emergency_date"}
_DATE_COLS_DEATH = {"lifeog_date", "death_date"}


def _nan_to_none(v: object) -> object:
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _parse_date(v: object) -> date | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    # YYYYMMDD integer format (e.g. 20220103)
    try:
        as_int = int(float(str(v)))
        s = str(as_int)
        if len(s) == 8:
            return pd.to_datetime(s, format="%Y%m%d").date()
    except (ValueError, OverflowError):
        pass
    parsed = pd.to_datetime(v, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _parse_int(v: object) -> int | None:
    v = _nan_to_none(v)
    if v is None:
        return None
    try:
        return int(float(str(v)))
    except (ValueError, TypeError):
        return None


def _parse_float(v: object) -> float | None:
    v = _nan_to_none(v)
    if v is None:
        return None
    try:
        return float(str(v))
    except (ValueError, TypeError):
        return None


def _parse_str(v: object, max_len: int | None = None) -> str | None:
    v = _nan_to_none(v)
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    if max_len:
        s = s[:max_len]
    return s


def _parse_list(v: object) -> list | None:
    v = _nan_to_none(v)
    if v is None:
        return None
    if isinstance(v, list):
        return v
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        import ast
        return ast.literal_eval(s)
    except Exception:
        return [s]


def _extract_hourly(row: pd.Series, prefix: str) -> list | None:
    vals = []
    for h in range(24):
        col = f"{prefix}_{h:02d}"
        v = _parse_float(row.get(col))
        vals.append(v)
    if all(v is None for v in vals):
        return None
    return vals


def _build_record(row: pd.Series, source_type: str) -> dict:
    date_cols = _DATE_COLS_EMERGENCY if source_type == "응급" else _DATE_COLS_DEATH

    def d(col: str) -> date | None:
        return _parse_date(row.get(col)) if col in date_cols else None

    return {
        "source_type": source_type,
        # 기본 정보
        "care_recipient_id": _parse_str(row.get("care_recipient_id"), 32) or "",
        "age": _parse_int(row.get("age")),
        "sex": _parse_str(row.get("sex"), 1),
        "alone": _parse_str(row.get("alone"), 1),
        "vision": _parse_str(row.get("vision"), 16),
        "hearing": _parse_str(row.get("hearing"), 16),
        "dosage": _parse_str(row.get("dosage"), 16),
        "district": _parse_str(row.get("district"), 64),
        "house_structure": _parse_str(row.get("house_structure"), 16),
        "room_no": _parse_int(row.get("room_no")),
        "bath_location": _parse_str(row.get("bath_location"), 16),
        # 이벤트 정보
        "lifeog_date": _parse_date(row.get("lifeog_date")),
        "emergency_date": _parse_date(row.get("emergency_date")),
        "emergency_record": _parse_str(row.get("emergency_record")),
        "occurrence_place": _parse_str(row.get("occurrence_place"), 32),
        "on_site": _parse_str(row.get("on_site"), 16),
        "hospital_transfer": _parse_str(row.get("hospital_transfer"), 16),
        "hospital_treatment": _parse_str(row.get("hospital_treatment"), 16),
        "death_date": _parse_date(row.get("death_date")),
        "death_record": _parse_str(row.get("death_record")),
        # 분석 데이터
        "place_code_1_list": _parse_list(row.get("place_code_1_list")),
        "aix_1_list": _parse_list(row.get("AIX_1_list")),
        "aix_h_list": _parse_list(row.get("AIX_h_list")),
        "aix_d": _parse_float(row.get("AIX_d")),
        "aix_1_eq_0_repeat_count": _parse_int(row.get("AIX_1_eq_0_repeat_count")),
        "total_aix_sum": _parse_float(row.get("total_aix_sum")),
        "total_aix_inc_ratio": _parse_float(row.get("total_aix_inc_ratio")),
        "night_aix_ratio": _parse_float(row.get("night_aix_ratio")),
        "total_age_aix_ratio": _parse_float(row.get("total_age_aix_ratio")),
        # 수면
        "sleep_depth_1_list": _parse_list(row.get("sleep_depth_1_list")),
        "sleep_start_time_d": _parse_str(row.get("sleep_start_time_d"), 8),
        "sleep_end_time_d": _parse_str(row.get("sleep_end_time_d"), 8),
        "total_sleep_period": _parse_float(row.get("total_sleep_period")),
        "total_sleep_aix_ratio": _parse_float(row.get("total_sleep_aix_ratio")),
        # 목욕
        "bath_count_d": _parse_int(row.get("bath_count_d")),
        "bath_time_d": _parse_float(row.get("bath_time_d")),
        "bath_nomove_time": _parse_float(row.get("bath_nomove_time")),
        "bath_count_in_sleep": _parse_int(row.get("bath_count_in_sleep")),
        "bath_time_per_count": _parse_float(row.get("bath_time_per_count")),
        "total_bath_average_count": _parse_float(row.get("total_bath_average_count")),
        # 외출
        "outgoing_1_list": _parse_list(row.get("outgoing_1_list")),
        "outgoing_count_d": _parse_int(row.get("outgoing_count_d")),
        "outgoing_time_d": _parse_float(row.get("outgoing_time_d")),
        "outgoing_late_night_count_d": _parse_int(row.get("outgoing_late_night_count_d")),
        "outgoing_late_night_time_d": _parse_float(row.get("outgoing_late_night_time_d")),
        "last_outgoing_time": _parse_str(row.get("last_outgoing_time"), 16),
        "total_outgoing_average_time": _parse_float(row.get("total_outgoing_average_time")),
        "total_outgoing_average_count": _parse_float(row.get("total_outgoing_average_count")),
        # 시간별 환경 센서
        "temp_list": _extract_hourly(row, "temp"),
        "humi_list": _extract_hourly(row, "humi"),
        "illu_list": _extract_hourly(row, "illu"),
    }


async def seed(reset: bool = False) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

    if reset:
        deleted = await AdlRawRecord.all().delete()
        print(f"기존 데이터 {deleted}건 삭제 완료")

    cnt = 0

    for file_path, source_type in [(EMERGENCY_FILE, "응급"), (DEATH_FILE, "사망")]:
        df = pd.read_excel(file_path, sheet_name=0)
        # care_recipient_id는 첫 행에만 있고 나머지는 빈 셀 (Excel 병합 셀 패턴)
        df["care_recipient_id"] = df["care_recipient_id"].ffill()
        print(f"[{source_type}] {len(df)}행 로드: {file_path.name}")

        for _, row in df.iterrows():
            data = _build_record(row, source_type)
            _, created = await AdlRawRecord.get_or_create(
                care_recipient_id=data["care_recipient_id"],
                lifeog_date=data["lifeog_date"],
                source_type=source_type,
                defaults=data,
            )
            if created:
                cnt += 1

    total = await AdlRawRecord.all().count()
    print(f"adl_raw_records: {cnt}건 생성 (총 {total}건)")
    print("시드 완료")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed(reset="--reset" in sys.argv))
