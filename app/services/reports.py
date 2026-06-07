"""보고서 목록 비즈니스 로직 — 위험등급 매핑·집계·일자 그룹핑 (순수 함수).

DB 접근 없이 단위 테스트 가능하도록, 라우터가 조회한 보고서 dict 리스트를 받아
요약 카운트와 일자별 그룹 구조로 변환한다.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from typing import Any

# 교차검증등급 → 위험 분류 (폴백 전용). 저장된 Report.risk_level 이 없을 때만 사용.
# 분류는 위험/주의/사망 3단계 ('정상' 없음 — C등급은 사망으로 표기).
LEVEL_TO_RISK = {"A": "위험", "B": "주의", "C": "사망"}
DEATH = "사망"

# 이상탐지 기반 분류 임계 (응급 그룹 내부를 위험/주의로 분할).
RISK_DUAL = 0.75  # dual 이상 비율 ≥ 0.75 → 위험
CAUTION_DUAL = 0.70  # 0.70 ≤ dual < 0.75 → 주의


def risk_of(level: str | None) -> str:
    """대상자 교차검증등급(A/B/C)을 위험/주의/사망으로 매핑. 미지정은 '사망'. (폴백)"""
    return LEVEL_TO_RISK.get((level or "").strip().upper(), DEATH)


def classify(label: str | None, dual_ratio: float | None) -> str | None:
    """AI 이상탐지 결과로 보고서 분류를 산정한다.

    - 사망 그룹(label='사망') → '사망' (전수)
    - 응급 그룹(label='응급') → dual 비율 ≥0.75 '위험', ≥0.70 '주의'
    - 그 외(평소·사망전·임계 미달) → None (보고서 대상 아님)
    """
    label = (label or "").strip()
    ratio = dual_ratio or 0.0
    if label == DEATH:
        return DEATH
    if label == "응급":
        if ratio >= RISK_DUAL:
            return "위험"
        if ratio >= CAUTION_DUAL:
            return "주의"
    return None


def risk_score(
    dual_ratio: float | None, mae_avg: float | None, activity_decline: float | None
) -> float:
    """이상탐지(dual 비율·MAE)와 지표 추세(활동량 감소율)를 결합한 0~1 위험점수.

    activity_decline 은 (1주차-4주차)/1주차 활동량 감소 비율(0~1)을 기대한다.
    """
    dual = max(0.0, min(1.0, dual_ratio or 0.0))
    mae = max(0.0, min(1.0, (mae_avg or 0.0) / 0.6))  # 사망 MAE≈0.58 을 상한 가정
    decline = max(0.0, min(1.0, activity_decline or 0.0))
    return round(min(1.0, 0.5 * dual + 0.2 * mae + 0.3 * decline), 2)


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
        # 저장된 분류(Report.risk_level) 우선, 없으면 등급에서 폴백.
        risk = item.get("risk_level") or risk_of(item.get("patient_level"))
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
