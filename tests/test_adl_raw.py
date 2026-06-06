from datetime import date

from httpx import AsyncClient

from app.models.adl_raw import AdlRawRecord


async def _make_adl(
    care_recipient_id: str = "R-001",
    **kwargs,
) -> AdlRawRecord:
    return await AdlRawRecord.create(
        source_type=kwargs.pop("source_type", "응급"),
        care_recipient_id=care_recipient_id,
        age=kwargs.pop("age", 80),
        sex=kwargs.pop("sex", "M"),
        alone=kwargs.pop("alone", "Y"),
        district=kwargs.pop("district", "노원구"),
        lifeog_date=kwargs.pop("lifeog_date", date(2026, 3, 10)),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/adl-raw/recipients  (person-grouped list)
# ---------------------------------------------------------------------------


async def test_recipients_unauthenticated_returns_401(client: AsyncClient):
    res = await client.get("/api/v1/adl-raw/recipients")
    assert res.status_code == 401


async def test_recipients_empty(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/adl-raw/recipients")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1
    assert data["page_size"] == 50


async def test_recipients_single_person_multi_records_groups(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="X", source_type="응급", lifeog_date=date(2026, 3, 10))
    await _make_adl(care_recipient_id="X", source_type="평소", lifeog_date=date(2026, 3, 11))
    await _make_adl(care_recipient_id="X", source_type="평소", lifeog_date=date(2026, 3, 12))

    res = await auth_client.get("/api/v1/adl-raw/recipients")
    data = res.json()["data"]
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["care_recipient_id"] == "X"
    assert item["total_records"] == 3
    assert item["source_type_counts"] == {"응급": 1, "평소": 2}
    assert item["last_event_date"] == "2026-03-12"
    assert item["first_event_date"] == "2026-03-10"


async def test_recipients_sort_by_most_recent_event(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="A", lifeog_date=date(2026, 3, 10))
    await _make_adl(care_recipient_id="B", lifeog_date=date(2026, 3, 15))

    res = await auth_client.get("/api/v1/adl-raw/recipients")
    items = res.json()["data"]["items"]
    assert [i["care_recipient_id"] for i in items] == ["B", "A"]


async def test_recipients_filter_preserves_full_history_counts(auth_client: AsyncClient):
    # Person X has both 응급 and 평소 records; filter narrows the set of matching
    # people but per-person counts must reflect that person's entire history.
    await _make_adl(care_recipient_id="X", source_type="응급", lifeog_date=date(2026, 3, 10))
    await _make_adl(care_recipient_id="X", source_type="평소", lifeog_date=date(2026, 3, 11))
    await _make_adl(care_recipient_id="X", source_type="평소", lifeog_date=date(2026, 3, 12))
    # Person Y has only 평소 — should not appear when filtered by source_type=응급.
    await _make_adl(care_recipient_id="Y", source_type="평소", lifeog_date=date(2026, 3, 13))

    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"source_type": "응급"})
    data = res.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["care_recipient_id"] == "X"
    assert item["total_records"] == 3
    assert item["source_type_counts"] == {"응급": 1, "평소": 2}


async def test_recipients_filter_by_sex(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="M-only", sex="M")
    await _make_adl(care_recipient_id="F-only", sex="F")

    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"sex": "F"})
    data = res.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["care_recipient_id"] == "F-only"
    assert data["items"][0]["sex"] == "F"


async def test_recipients_filter_by_alone(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="alone-Y", alone="Y")
    await _make_adl(care_recipient_id="alone-N", alone="N")

    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"alone": "Y"})
    items = res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["care_recipient_id"] == "alone-Y"


async def test_recipients_filter_by_district(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="N1", district="노원구")
    await _make_adl(care_recipient_id="G1", district="강남구")

    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"district": "노원구"})
    items = res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["care_recipient_id"] == "N1"


async def test_recipients_filter_by_age_range(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="young", age=70)
    await _make_adl(care_recipient_id="mid", age=80)
    await _make_adl(care_recipient_id="old", age=90)

    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"age_min": 75, "age_max": 85})
    items = res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["care_recipient_id"] == "mid"


async def test_recipients_filter_by_q(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="ALPHA-001")
    await _make_adl(care_recipient_id="BETA-002")

    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"q": "ALPHA"})
    items = res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["care_recipient_id"] == "ALPHA-001"


async def test_recipients_age_min_greater_than_max_returns_422(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"age_min": 90, "age_max": 70})
    assert res.status_code == 422


async def test_recipients_page_size_over_200_returns_422(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/adl-raw/recipients", params={"page_size": 201})
    assert res.status_code == 422


async def test_recipients_pagination(auth_client: AsyncClient):
    for i in range(60):
        # Unique recipient id per record → 60 distinct people.
        await _make_adl(
            care_recipient_id=f"R-{i:03d}",
            lifeog_date=date(2026, 3, 1) if i % 2 == 0 else date(2026, 3, 2),
        )

    res1 = await auth_client.get("/api/v1/adl-raw/recipients", params={"page": 1, "page_size": 25})
    res2 = await auth_client.get("/api/v1/adl-raw/recipients", params={"page": 2, "page_size": 25})
    res3 = await auth_client.get("/api/v1/adl-raw/recipients", params={"page": 3, "page_size": 25})

    assert res1.json()["data"]["total"] == 60
    assert len(res1.json()["data"]["items"]) == 25
    assert len(res2.json()["data"]["items"]) == 25
    assert len(res3.json()["data"]["items"]) == 10

    # No recipient appears in two pages.
    ids1 = {i["care_recipient_id"] for i in res1.json()["data"]["items"]}
    ids2 = {i["care_recipient_id"] for i in res2.json()["data"]["items"]}
    ids3 = {i["care_recipient_id"] for i in res3.json()["data"]["items"]}
    assert ids1.isdisjoint(ids2)
    assert ids1.isdisjoint(ids3)
    assert ids2.isdisjoint(ids3)
    assert len(ids1 | ids2 | ids3) == 60


async def test_recipients_items_omit_timeseries_keys(auth_client: AsyncClient):
    """Regression guard — recipient rows must never expose raw timeseries arrays."""
    await _make_adl()

    res = await auth_client.get("/api/v1/adl-raw/recipients")
    item = res.json()["data"]["items"][0]
    for forbidden_key in (
        "aix_h_list",
        "temp_list",
        "humi_list",
        "illu_list",
        "outgoing_1_list",
        "place_code_1_list",
        "aix_1_list",
        "sleep_depth_1_list",
    ):
        assert forbidden_key not in item, (
            f"Recipient item must not expose timeseries key {forbidden_key}"
        )


# ---------------------------------------------------------------------------
# GET /api/v1/adl-raw/recipients/{recipient_id}/records
# ---------------------------------------------------------------------------


async def test_recipient_records_unauthenticated_returns_401(client: AsyncClient):
    res = await client.get("/api/v1/adl-raw/recipients/R-001/records")
    assert res.status_code == 401


async def test_recipient_records_unknown_returns_404(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/adl-raw/recipients/NOT-EXIST/records")
    assert res.status_code == 404


async def test_recipient_records_returns_all_dates_for_one_person(
    auth_client: AsyncClient,
):
    await _make_adl(care_recipient_id="X", lifeog_date=date(2026, 3, 10))
    await _make_adl(care_recipient_id="X", lifeog_date=date(2026, 3, 12))
    await _make_adl(care_recipient_id="X", lifeog_date=date(2026, 3, 11))
    # Different person — must not appear.
    await _make_adl(care_recipient_id="Y", lifeog_date=date(2026, 3, 15))

    res = await auth_client.get("/api/v1/adl-raw/recipients/X/records")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["care_recipient_id"] == "X"
    assert len(data["items"]) == 3
    # Sorted by lifeog_date desc.
    assert [it["lifeog_date"] for it in data["items"]] == [
        "2026-03-12",
        "2026-03-11",
        "2026-03-10",
    ]


async def test_recipient_records_pagination(auth_client: AsyncClient):
    # Arrange — 3 records for one recipient, distinct descending dates
    for day in (10, 11, 12):
        await _make_adl(care_recipient_id="X", lifeog_date=date(2026, 3, day))

    # Act — page 1 of size 2, then page 2
    p1 = await auth_client.get(
        "/api/v1/adl-raw/recipients/X/records", params={"page": 1, "page_size": 2}
    )
    p2 = await auth_client.get(
        "/api/v1/adl-raw/recipients/X/records", params={"page": 2, "page_size": 2}
    )

    # Assert — total reported across pages; page slices are disjoint and correctly sized
    d1, d2 = p1.json()["data"], p2.json()["data"]
    assert d1["total"] == 3 and d2["total"] == 3
    assert d1["page"] == 1 and d1["page_size"] == 2
    assert len(d1["items"]) == 2 and len(d2["items"]) == 1
    ids1 = {it["id"] for it in d1["items"]}
    ids2 = {it["id"] for it in d2["items"]}
    assert ids1.isdisjoint(ids2)


async def test_recipient_records_omit_timeseries_keys(auth_client: AsyncClient):
    await _make_adl(care_recipient_id="X")

    res = await auth_client.get("/api/v1/adl-raw/recipients/X/records")
    item = res.json()["data"]["items"][0]
    for forbidden_key in (
        "aix_h_list",
        "temp_list",
        "humi_list",
        "illu_list",
        "outgoing_1_list",
        "place_code_1_list",
        "aix_1_list",
        "sleep_depth_1_list",
    ):
        assert forbidden_key not in item


# ---------------------------------------------------------------------------
# GET /api/v1/adl-raw/{record_id}  (daily detail — unchanged behavior)
# ---------------------------------------------------------------------------


async def test_detail_adl_raw_unauthenticated_returns_401(client: AsyncClient):
    res = await client.get("/api/v1/adl-raw/1")
    assert res.status_code == 401


async def test_detail_adl_raw_success(auth_client: AsyncClient):
    record = await _make_adl(
        aix_d=1.5,
        total_aix_sum=36.0,
        night_aix_ratio=0.4,
        total_sleep_period=7.5,
        outgoing_count_d=2,
    )

    res = await auth_client.get(f"/api/v1/adl-raw/{record.id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == record.id
    assert data["source_type"] == "응급"
    assert data["care_recipient_id"] == "R-001"
    assert data["aix_d"] == 1.5
    assert data["total_aix_sum"] == 36.0
    assert data["night_aix_ratio"] == 0.4
    assert data["total_sleep_period"] == 7.5
    # Array fields are NULL under SQLite — presence in schema is enough.
    assert "aix_h_list" in data
    assert "outgoing_24h" in data
    assert "sleep_depth_24h" in data


async def test_detail_adl_raw_404(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/adl-raw/99999")
    assert res.status_code == 404


def test_detail_adl_raw_outgoing_sentinel_stripped():
    """SQLite cannot store ArrayField values via ORM, so this test validates
    the transform logic directly (same contract as the router uses)."""
    from app.services.adl_raw_transform import aggregate_outgoing_to_24h

    outgoing_24h = aggregate_outgoing_to_24h([254] * 1440)
    assert outgoing_24h is not None
    assert all(v == 0 for v in outgoing_24h), f"Expected all zeros but got: {outgoing_24h}"


def test_detail_adl_raw_outgoing_24h_aggregation():
    """SQLite cannot store ArrayField values via ORM, so this test validates
    the transform logic directly (same contract as the router uses)."""
    from app.services.adl_raw_transform import aggregate_outgoing_to_24h

    outgoing_list = [0] * 1440
    outgoing_list[0] = 1
    outgoing_24h = aggregate_outgoing_to_24h(outgoing_list)
    assert outgoing_24h is not None
    assert outgoing_24h[0] == 1
    assert all(v == 0 for v in outgoing_24h[1:])
