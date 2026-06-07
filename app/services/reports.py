"""보고서 목록 비즈니스 로직 — 위험등급 매핑·집계·일자 그룹핑 (순수 함수).

DB 접근 없이 단위 테스트 가능하도록, 라우터가 조회한 보고서 dict 리스트를 받아
요약 카운트와 일자별 그룹 구조로 변환한다.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from typing import Any

# 교차검증등급 → 위험 분류. Patient.cross_verification_level 이 단일 출처다.
# 분류는 위험/주의/사망 3단계 ('정상' 없음 — C등급은 사망으로 표기).
LEVEL_TO_RISK = {"A": "위험", "B": "주의", "C": "사망"}
DEATH = "사망"


def risk_of(level: str | None) -> str:
    """대상자 교차검증등급(A/B/C)을 위험/주의/사망으로 매핑. 미지정은 '사망'."""
    return LEVEL_TO_RISK.get((level or "").strip().upper(), DEATH)


def build_report_list(items: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """보고서 dict 리스트를 요약 카운트 + 일자별 그룹으로 변환한다.

    Args:
        items: 각 dict 는 최소 `patient_level`(str|None), `generated_at`(datetime) 보유.
               그 외 필드는 그대로 보존해 응답 항목으로 전달된다. 호출 측에서
               generated_at 내림차순 정렬을 전달하면 그룹·항목 순서가 최신순이 된다.
        today: '오늘' 기준 날짜 (순수성을 위해 주입).

    Returns:
        {risk_count, caution_count, death_count, total, today_count, groups}
        groups = [{date, count, items}] (최신일 우선).
    """
    risk_count = caution_count = death_count = today_count = 0
    groups: OrderedDict[date, dict[str, Any]] = OrderedDict()

    for item in items:
        risk = risk_of(item.get("patient_level"))
        item = {**item, "risk_level": risk}

        if risk == "위험":
            risk_count += 1
        elif risk == "주의":
            caution_count += 1
        else:  # 사망
            death_count += 1

        generated_at: datetime = item["generated_at"]
        day = generated_at.date()
        if day == today:
            today_count += 1

        group = groups.get(day)
        if group is None:
            group = {"date": day, "count": 0, "items": []}
            groups[day] = group
        group["count"] += 1
        group["items"].append(item)

    return {
        "risk_count": risk_count,
        "caution_count": caution_count,
        "death_count": death_count,
        "total": len(items),
        "today_count": today_count,
        "groups": list(groups.values()),
    }
