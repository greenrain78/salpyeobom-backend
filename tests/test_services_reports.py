from datetime import UTC, date, datetime

from app.services.reports import build_report_list, classify, risk_of, risk_score


def test_risk_of_mapping():
    assert risk_of("A") == "위험"
    assert risk_of("B") == "주의"
    assert risk_of("C") == "사망"
    assert risk_of(None) == "사망"
    assert risk_of("") == "사망"
    assert risk_of("a") == "위험"  # 대소문자 무시


def test_classify_thresholds():
    # 사망 그룹은 비율과 무관하게 사망
    assert classify("사망", 1.0) == "사망"
    assert classify("사망", 0.0) == "사망"
    # 응급 그룹: ≥0.75 위험, ≥0.70 주의, 그 외 None
    assert classify("응급", 0.80) == "위험"
    assert classify("응급", 0.75) == "위험"
    assert classify("응급", 0.74) == "주의"
    assert classify("응급", 0.70) == "주의"
    assert classify("응급", 0.69) is None
    # 평소·미상은 대상 아님
    assert classify("평소(30%)", 1.0) is None
    assert classify(None, None) is None


def test_risk_score_bounds_and_blend():
    assert risk_score(0.0, 0.0, 0.0) == 0.0
    assert risk_score(1.0, 0.6, 1.0) == 1.0  # 0.5+0.2+0.3, 상한 클램프
    # 0.5*0.7 + 0.2*(0.2/0.6) + 0.3*0.5 = 0.5667 → 0.57
    assert risk_score(0.7, 0.2, 0.5) == 0.57
    # None 은 0 으로 처리
    assert risk_score(None, None, 0.0) == 0.0


def _item(rid, level, day):
    return {
        "id": rid,
        "patient_id": str(rid),
        "patient_name": f"환자{rid}",
        "patient_level": level,
        "title": "보고서",
        "file_name": f"r{rid}.pdf",
        "generated_at": datetime(day.year, day.month, day.day, tzinfo=UTC),
    }


def test_build_report_list_counts_groups_and_today():
    today = date(2026, 6, 7)
    items = [
        _item(1, "A", date(2026, 6, 7)),
        _item(2, "B", date(2026, 6, 7)),
        _item(3, "C", date(2026, 6, 6)),
    ]

    data = build_report_list(items, today=today)

    assert data["risk_count"] == 1
    assert data["caution_count"] == 1
    assert data["death_count"] == 1
    assert data["total"] == 3
    assert data["today_count"] == 2

    # 일자별 그룹 (입력 순서 유지 → 최신일 우선)
    assert [g["date"] for g in data["groups"]] == [date(2026, 6, 7), date(2026, 6, 6)]
    assert data["groups"][0]["count"] == 2
    # risk_level 이 각 항목에 주입됨
    assert data["groups"][0]["items"][0]["risk_level"] == "위험"
    assert data["groups"][1]["items"][0]["risk_level"] == "사망"


def test_build_report_list_prefers_stored_risk_level():
    # 저장된 risk_level 이 있으면 등급(patient_level)보다 우선한다.
    item = _item(1, "A", date(2026, 6, 7))  # 등급 A → 폴백이면 위험
    item["risk_level"] = "주의"  # 저장값
    data = build_report_list([item], today=date(2026, 6, 7))
    assert data["caution_count"] == 1
    assert data["risk_count"] == 0
    assert data["groups"][0]["items"][0]["risk_level"] == "주의"


def test_build_report_list_empty():
    data = build_report_list([], today=date(2026, 6, 7))
    assert data["total"] == 0
    assert data["today_count"] == 0
    assert data["groups"] == []
