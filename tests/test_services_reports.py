from datetime import UTC, date, datetime

from app.services.reports import build_report_list, risk_of


def test_risk_of_mapping():
    assert risk_of("A") == "위험"
    assert risk_of("B") == "주의"
    assert risk_of("C") == "사망"
    assert risk_of(None) == "사망"
    assert risk_of("") == "사망"
    assert risk_of("a") == "위험"  # 대소문자 무시


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


def test_build_report_list_empty():
    data = build_report_list([], today=date(2026, 6, 7))
    assert data["total"] == 0
    assert data["today_count"] == 0
    assert data["groups"] == []
