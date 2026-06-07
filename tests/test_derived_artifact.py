"""커밋된 파생 아티팩트 data/derived/patients.jsonl 의 형식·정합 검증.

이 아티팩트는 adl_raw_records 에서 오프라인 1회 파생해 고정한 단일 진실이며,
scripts/load_derived.py 가 그대로 적재한다. 형식이 깨지면 적재가 깨지므로 가드한다.
"""

import json
from datetime import datetime
from pathlib import Path

from app.models.enums import ActionStatus

_DERIVED = Path(__file__).resolve().parents[1] / "data" / "derived"
ARTIFACT = _DERIVED / "patients.jsonl"

_REQUIRED_PATIENT_KEYS = {
    "patient_id",
    "name",
    "age",
    "address_full",
    "address_summary",
    "diseases",
    "cross_verification_level",
    "ai_alert_title",
    "ai_alert_desc",
    "doc_no",
    "next_visit_time",
    "next_visit_plan",
    "profile_image_url",
    "situations",
}
_VALID_STATUSES = {s.value for s in ActionStatus}


def _records() -> list[dict]:
    text = ARTIFACT.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_artifact_exists_and_nonempty() -> None:
    assert ARTIFACT.exists(), f"누락된 아티팩트: {ARTIFACT}"
    assert _records(), "아티팩트가 비어 있다"


def test_every_record_has_required_keys() -> None:
    for rec in _records():
        missing = _REQUIRED_PATIENT_KEYS - rec.keys()
        assert not missing, f"{rec.get('patient_id')} 누락 키: {missing}"
        assert isinstance(rec["diseases"], list)
        assert isinstance(rec["age"], int)


def test_grades_are_valid() -> None:
    for rec in _records():
        assert rec["cross_verification_level"] in {"A", "B", "C", None}


def test_situations_are_well_formed() -> None:
    for rec in _records():
        for s in rec["situations"]:
            assert s["action_status"] in _VALID_STATUSES
            assert s["category"]
            # occurred_at 은 datetime 으로 파싱 가능해야 한다(적재기가 fromisoformat 사용).
            datetime.fromisoformat(s["occurred_at"])


def test_active_situations_match_grade_rules() -> None:
    # C등급은 활성 상황(미완료)이 없어야 한다. A→낙상(응급 버킷), B→미응답/지연(경고 버킷).
    for rec in _records():
        active = [
            s for s in rec["situations"] if s["action_status"] != ActionStatus.COMPLETED.value
        ]
        grade = rec["cross_verification_level"]
        if grade == "C":
            assert active == [], f"{rec['patient_id']} C등급인데 활성 상황 존재"
        elif grade == "A":
            assert any("낙상" in s["category"] for s in active)
        elif grade == "B":
            assert any(s["category"] in {"미응답", "지연"} for s in active)


def test_dashboard_buckets_are_nonzero() -> None:
    # 데모 목적: 아티팩트가 응급·경고·정상 버킷을 모두 채우는지(0이 아닌지) 보장.
    emergency = warning = 0
    for rec in _records():
        for s in rec["situations"]:
            if s["action_status"] == ActionStatus.COMPLETED.value:
                continue
            if "낙상" in s["category"] or "응급" in s["category"]:
                emergency += 1
            elif s["category"] in {"미응답", "지연"}:
                warning += 1
    total = len(_records())
    assert emergency >= 1
    assert warning >= 1
    assert total - emergency - warning >= 1  # 정상 버킷도 비지 않음


# ---------------------------------------------------------------------------
# SYN 합성 환자 아티팩트 (data/derived/patients_syn.jsonl) — 전체 필드 + 상황
# ---------------------------------------------------------------------------

SYN_ARTIFACT = _DERIVED / "patients_syn.jsonl"


def _syn_records() -> list[dict]:
    text = SYN_ARTIFACT.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_syn_artifact_exists_and_nonempty() -> None:
    assert SYN_ARTIFACT.exists(), f"누락된 SYN 아티팩트: {SYN_ARTIFACT}"
    assert _syn_records()


def test_syn_records_well_formed() -> None:
    seen: set[str] = set()
    for rec in _syn_records():
        missing = _REQUIRED_PATIENT_KEYS - rec.keys()
        assert not missing, f"{rec.get('patient_id')} 누락 키: {missing}"
        assert rec["cross_verification_level"] in {"A", "B", "C"}
        assert isinstance(rec["age"], int)
        assert rec["patient_id"].startswith("SYN-")
        assert rec["patient_id"] not in seen
        seen.add(rec["patient_id"])
        for s in rec["situations"]:
            assert s["action_status"] in _VALID_STATUSES
            datetime.fromisoformat(s["occurred_at"])


def test_syn_grade_situation_consistency() -> None:
    # 응급 시나리오→A(활성=응급 버킷, 시나리오 기반 다양한 category),
    # 사망→C(활성 없음, 과거 사망 완료), C등급→활성 없음.
    for rec in _syn_records():
        kind = rec["patient_id"].split("-")[1]  # 평소/응급/사망
        grade = rec["cross_verification_level"]
        active = [
            s for s in rec["situations"] if s["action_status"] != ActionStatus.COMPLETED.value
        ]
        if kind == "사망":
            assert grade == "C"
            assert active == []
            assert any(s["category"] == "사망" for s in rec["situations"])
        elif kind == "응급":
            assert grade == "A"
            # 활성 상황은 응급 버킷(낙상/응급 키워드) — 시나리오에 따라 낙상/심혈관/탈수·쇠약/의식저하
            assert any(("낙상" in s["category"] or "응급" in s["category"]) for s in active)
        if grade == "C":
            assert active == []


def test_syn_emergency_categories_are_varied() -> None:
    # "전부 낙상 의심"이 아니라 시나리오 기반으로 분산되었는지 보장.
    cats = {
        s["category"]
        for rec in _syn_records()
        for s in rec["situations"]
        if s["action_status"] != ActionStatus.COMPLETED.value
        and rec["patient_id"].startswith("SYN-응급")
    }
    assert len(cats) >= 3, f"응급 활성 category 다양성 부족: {cats}"
