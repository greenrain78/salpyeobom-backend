"""scripts/load_derived.py (JSONL → DB 적재기) 단위·통합 테스트.

라이브 LLM 호출 없음 — 작은 JSONL 픽스처만 사용한다.
conftest 의 `client`/`auth_client` 픽스처가 Tortoise(SQLite in-memory)를 초기화하므로,
적재기는 그 컨텍스트에서 모델에 직접 접근한다.
"""

import json
from pathlib import Path

from httpx import AsyncClient

from app.models.enums import ActionStatus
from app.models.patient import Patient, Situation
from scripts.load_derived import load_derived, parse_records

# A등급(활성 낙상) 1명 + C등급(활성 없음, 과거 사망) 1명.
_FIXTURE = [
    {
        "patient_id": "T1",
        "name": "테스트환자",
        "age": 81,
        "address_full": "서울시 강남구 테헤란로 1",
        "address_summary": "강남구 역삼동",
        "phone_number": None,
        "manager_name": "담당자",
        "management_level": "집중 관리군 (1등급)",
        "diseases": ["고혈압", "골다공증"],
        "cross_verification_level": "A",
        "ai_alert_title": "낙상 고위험",
        "ai_alert_desc": "야간 활동 급증",
        "doc_no": "2026-0001",
        "next_visit_time": "2026-06-09 14:00",
        "next_visit_plan": "낙상 위험 재평가",
        "profile_image_url": None,
        "situations": [
            {
                "category": "낙상 의심",
                "detail_reason": "독거 낙상 위험",
                "occurred_at": "2026-06-07T05:00:00+00:00",
                "action_status": "조치 대기",
            }
        ],
    },
    {
        "patient_id": "T2",
        "name": "고인",
        "age": 85,
        "address_full": "경북 성주군 성주읍 1",
        "address_summary": "성주군 성주읍",
        "phone_number": None,
        "manager_name": "담당자2",
        "management_level": "자립 관리군 (3등급)",
        "diseases": ["고혈압"],
        "cross_verification_level": "C",
        "ai_alert_title": "모니터링 종료",
        "ai_alert_desc": "노환 사망",
        "doc_no": "2026-0002",
        "next_visit_time": None,
        "next_visit_plan": None,
        "profile_image_url": None,
        "situations": [
            {
                "category": "사망",
                "detail_reason": "노환으로 인한 사망",
                "occurred_at": "2023-03-31T00:00:00+00:00",
                "action_status": "조치 완료",
            }
        ],
    },
]


def _write_fixture(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "patients.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    return path


def test_parse_records_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "p.jsonl"
    path.write_text('{"patient_id": "X"}\n\n  \n{"patient_id": "Y"}\n', encoding="utf-8")
    records = parse_records(path)
    assert [r["patient_id"] for r in records] == ["X", "Y"]


async def test_load_inserts_patients_and_situations(client: AsyncClient, tmp_path: Path) -> None:
    path = _write_fixture(tmp_path, _FIXTURE)

    patients, situations = await load_derived(path)

    assert (patients, situations) == (2, 2)
    t1 = await Patient.get(patient_id="T1")
    assert t1.name == "테스트환자"
    assert t1.cross_verification_level == "A"
    assert t1.ai_alert_title == "낙상 고위험"
    assert t1.diseases == ["고혈압", "골다공증"]
    assert t1.doc_no == "2026-0001"
    assert t1.next_visit_time == "2026-06-09 14:00"

    sit = await Situation.get(patient=t1)
    assert sit.category == "낙상 의심"
    assert sit.action_status == ActionStatus.PENDING
    assert sit.is_active is True

    # 과거 사망은 완료 상태(활성 아님)
    dead_sit = await Situation.get(patient=await Patient.get(patient_id="T2"))
    assert dead_sit.action_status == ActionStatus.COMPLETED
    assert dead_sit.is_active is False


async def test_load_is_idempotent(client: AsyncClient, tmp_path: Path) -> None:
    path = _write_fixture(tmp_path, _FIXTURE)
    await load_derived(path)
    await load_derived(path)  # 재실행

    assert await Patient.all().count() == 2
    # 상황도 환자당 새로고침되어 중복 누적되지 않는다.
    assert await Situation.all().count() == 2


async def test_load_upserts_changed_fields(client: AsyncClient, tmp_path: Path) -> None:
    await load_derived(_write_fixture(tmp_path, _FIXTURE))

    updated = json.loads(json.dumps(_FIXTURE))
    updated[0]["cross_verification_level"] = "B"
    updated[0]["name"] = "이름변경"
    updated[0]["situations"] = []  # 활성 상황 제거
    await load_derived(_write_fixture(tmp_path, updated))

    t1 = await Patient.get(patient_id="T1")
    assert t1.cross_verification_level == "B"
    assert t1.name == "이름변경"
    assert await Situation.filter(patient=t1).count() == 0


async def test_load_without_situations_key_preserves_existing(
    client: AsyncClient, tmp_path: Path
) -> None:
    # 기존 상황이 있는 환자에 'situations' 키 없는 레코드로 필드만 보강 → 상황 보존.
    await load_derived(_write_fixture(tmp_path, _FIXTURE))
    t1 = await Patient.get(patient_id="T1")
    assert await Situation.filter(patient=t1).count() == 1  # 적재된 활성 상황

    enrich = {
        "patient_id": "T1",
        "cross_verification_level": "B",
        "ai_alert_title": "보강된 제목",
    }  # situations 키 없음
    patients, situations = await load_derived(_write_fixture(tmp_path, [enrich]))

    assert (patients, situations) == (1, 0)
    t1 = await Patient.get(patient_id="T1")
    assert t1.cross_verification_level == "B"  # 컬럼 보강됨
    assert t1.name == "테스트환자"  # 기존 이름 보존
    assert await Situation.filter(patient=t1).count() == 1  # 기존 상황 보존(미삭제)


async def test_loaded_data_drives_endpoints(auth_client: AsyncClient, tmp_path: Path) -> None:
    # 적재 결과가 대시보드·활성 상황·환자 상세에 그대로 반영되는 end-to-end 흐름.
    await load_derived(_write_fixture(tmp_path, _FIXTURE))

    summary = (await auth_client.get("/api/v1/dashboard/summary")).json()["data"]
    assert summary["total_monitoring_count"] == 2
    assert summary["emergency_count"] == 1  # "낙상 의심"
    assert summary["normal_count"] == 1

    active = (await auth_client.get("/api/v1/situations/active")).json()["data"]["situations"]
    assert [s["category"] for s in active] == ["낙상 의심"]

    detail = (await auth_client.get("/api/v1/patients/T1/details")).json()["data"]
    assert detail["ai_analysis"]["alert_title"] == "낙상 고위험"
    assert detail["doc_no"] == "2026-0001"
