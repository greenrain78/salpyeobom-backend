from httpx import AsyncClient

from app.models.patient import Patient


async def _make_patient(pid: str = "user_1001", **kwargs) -> Patient:
    return await Patient.create(
        patient_id=pid,
        name=kwargs.get("name", "김순자"),
        age=kwargs.get("age", 78),
        address_full=kwargs.get("address_full", "서울특별시 노원구 상계동 123-4"),
        address_summary=kwargs.get("address_summary", "상계동 123-4"),
        manager_name="김재섭",
        management_level="집중 관리군 (1등급)",
        diseases=["고혈압", "초기 치매"],
        cross_verification_level=kwargs.get("cross_verification_level"),
        ai_alert_title=kwargs.get("ai_alert_title"),
        ai_alert_desc=kwargs.get("ai_alert_desc"),
        doc_no=kwargs.get("doc_no"),
        next_visit_time=kwargs.get("next_visit_time"),
        next_visit_plan=kwargs.get("next_visit_plan"),
        profile_image_url=kwargs.get("profile_image_url"),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/patients
# ---------------------------------------------------------------------------


async def test_list_patients_empty(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/patients")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_count"] == 0
    assert data["patients"] == []


async def test_list_patients_pagination(auth_client: AsyncClient):
    for i in range(5):
        await _make_patient(pid=f"p{i}", name=f"환자{i}")

    res = await auth_client.get("/api/v1/patients", params={"page": 1, "limit": 3})
    data = res.json()["data"]
    assert data["total_count"] == 5
    assert data["total_pages"] == 2
    assert len(data["patients"]) == 3

    res2 = await auth_client.get("/api/v1/patients", params={"page": 2, "limit": 3})
    assert len(res2.json()["data"]["patients"]) == 2


async def test_list_patients_search(auth_client: AsyncClient):
    await _make_patient(pid="p1", name="김순자")
    await _make_patient(pid="p2", name="최갑수")

    res = await auth_client.get("/api/v1/patients", params={"search_name": "김"})
    data = res.json()["data"]
    assert data["total_count"] == 1
    assert data["patients"][0]["name"] == "김순자"


async def test_list_patients_fields(auth_client: AsyncClient):
    await _make_patient()
    item = (await auth_client.get("/api/v1/patients")).json()["data"]["patients"][0]
    assert item["patient_id"] == "user_1001"
    assert item["manager_name"] == "김재섭"
    assert "hashed_password" not in item


async def test_list_patients_exposes_cross_verification_level(auth_client: AsyncClient):
    # 프론트 목록의 등급 배지는 cross_verification_level 을 읽는다.
    await _make_patient(pid="a", cross_verification_level="A")
    await _make_patient(pid="c")  # 미설정 → null
    by_id = {
        p["patient_id"]: p
        for p in (await auth_client.get("/api/v1/patients")).json()["data"]["patients"]
    }
    assert by_id["a"]["cross_verification_level"] == "A"
    assert by_id["c"]["cross_verification_level"] is None


# ---------------------------------------------------------------------------
# GET /api/v1/patients/{patient_id}/details
# ---------------------------------------------------------------------------


async def test_patient_details_success(auth_client: AsyncClient):
    await _make_patient()
    res = await auth_client.get("/api/v1/patients/user_1001/details")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["name"] == "김순자"
    assert data["age"] == "만 78세"
    assert data["administration"]["diseases"] == ["고혈압", "초기 치매"]


async def test_patient_details_not_found(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/patients/ghost/details")
    assert res.status_code == 404


async def test_patient_details_includes_derived_fields(auth_client: AsyncClient):
    # 상세 패널: AI 분석(경보 제목/본문/등급)·문서번호·방문일정·프로필 이미지.
    await _make_patient(
        cross_verification_level="A",
        ai_alert_title="낙상 고위험",
        ai_alert_desc="야간 활동 급증",
        doc_no="2026-0661",
        next_visit_time="2026-06-09 14:00",
        next_visit_plan="낙상 위험 재평가",
    )
    data = (await auth_client.get("/api/v1/patients/user_1001/details")).json()["data"]

    assert data["cross_verification_level"] == "A"
    assert data["doc_no"] == "2026-0661"
    assert data["profile_image_url"] is None
    # 프론트는 ai_analysis.cross_verification_level 로 경보 테마를 정한다.
    assert data["ai_analysis"] == {
        "cross_verification_level": "A",
        "alert_title": "낙상 고위험",
        "alert_desc": "야간 활동 급증",
    }
    assert data["administration"]["next_visit_time"] == "2026-06-09 14:00"
    assert data["administration"]["next_visit_plan"] == "낙상 위험 재평가"


async def test_patient_details_derived_fields_nullable(auth_client: AsyncClient):
    # 파생 메타 미적재 대상자도 깨지지 않는다(모두 nullable).
    await _make_patient()
    data = (await auth_client.get("/api/v1/patients/user_1001/details")).json()["data"]
    assert data["cross_verification_level"] is None
    assert data["ai_analysis"]["alert_title"] is None
    assert data["administration"]["next_visit_time"] is None
