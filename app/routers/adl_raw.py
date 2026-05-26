from collections import Counter, defaultdict
from datetime import date
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.dependencies import get_current_user
from app.models.adl_raw import AdlRawRecord
from app.schemas.adl_raw import (
    AdlRawDetail,
    AdlRawListData,
    AdlRawListItem,
    AdlRawRecipientItem,
    AdlRawRecipientRecordsData,
    AdlRawRecipientsData,
    AdlRawRecordSummary,
)
from app.schemas.common import SuccessResponse
from app.services.adl_raw_transform import (
    aggregate_outgoing_to_24h,
    aggregate_sleep_depth_to_24h,
    recount_outgoing_count_d,
)

router = APIRouter(
    prefix="/api/v1/adl-raw",
    tags=["adl-raw"],
    dependencies=[Depends(get_current_user)],
)

# Scalar fields for the root list endpoint (per-row, no arrays).
_LIST_FIELDS = (
    "id",
    "care_recipient_id",
    "source_type",
    "age",
    "sex",
    "alone",
    "district",
    "lifeog_date",
    "emergency_date",
    "death_date",
    "aix_d",
    "total_aix_sum",
    "night_aix_ratio",
    "outgoing_count_d",
)

# Scalar fields needed for recipient-level aggregation (sort-by-recent + demographics).
# `id` is included for deterministic tie-break when multiple rows share the latest lifeog_date.
_AGGREGATE_FIELDS = (
    "id",
    "care_recipient_id",
    "source_type",
    "age",
    "sex",
    "alone",
    "district",
    "lifeog_date",
    "emergency_date",
    "death_date",
)

# Scalar fields shown in a recipient's per-record list (excludes 1440-element arrays).
_RECORD_SUMMARY_FIELDS = (
    "id",
    "source_type",
    "lifeog_date",
    "emergency_date",
    "death_date",
    "aix_d",
    "total_aix_sum",
    "night_aix_ratio",
    "outgoing_count_d",
)


@router.get("", response_model=SuccessResponse[AdlRawListData])
async def list_adl_raw(
    source_type: str | None = Query(default=None),
    sex: str | None = Query(default=None),
    alone: str | None = Query(default=None),
    district: str | None = Query(default=None),
    age_min: int | None = Query(default=None, ge=0),
    age_max: int | None = Query(default=None, ge=0),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> SuccessResponse[AdlRawListData]:
    if age_min is not None and age_max is not None and age_min > age_max:
        raise HTTPException(
            status_code=422,
            detail="age_min must be less than or equal to age_max.",
        )

    qs = AdlRawRecord.all()
    if source_type:
        qs = qs.filter(source_type=source_type)
    if sex:
        qs = qs.filter(sex=sex)
    if alone:
        qs = qs.filter(alone=alone)
    if district:
        qs = qs.filter(district=district)
    if age_min is not None:
        qs = qs.filter(age__gte=age_min)
    if age_max is not None:
        qs = qs.filter(age__lte=age_max)
    if q:
        qs = qs.filter(care_recipient_id__icontains=q)

    total = await qs.count()

    agg_rows = await qs.only("source_type", "care_recipient_id")
    source_type_counts: dict[str, int] = dict(Counter(r.source_type for r in agg_rows))
    unique_recipient_count = len({r.care_recipient_id for r in agg_rows})

    page_rows = await (
        qs.only(*_LIST_FIELDS)
        .order_by("-lifeog_date", "-id")
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [AdlRawListItem.model_validate(r) for r in page_rows]

    return SuccessResponse(
        data=AdlRawListData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            source_type_counts=source_type_counts,
            unique_recipient_count=unique_recipient_count,
        )
    )


def _event_date(row: AdlRawRecord) -> date | None:
    """Most informative single event date for sorting — lifeog over emergency over death."""
    return row.lifeog_date or row.emergency_date or row.death_date


@router.get("/recipients", response_model=SuccessResponse[AdlRawRecipientsData])
async def list_recipients(
    source_type: str | None = Query(default=None),
    sex: str | None = Query(default=None),
    alone: str | None = Query(default=None),
    district: str | None = Query(default=None),
    age_min: int | None = Query(default=None, ge=0),
    age_max: int | None = Query(default=None, ge=0),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> SuccessResponse[AdlRawRecipientsData]:
    if age_min is not None and age_max is not None and age_min > age_max:
        raise HTTPException(
            status_code=422,
            detail="age_min must be less than or equal to age_max.",
        )

    # Pass 1 — filtered query returns care_recipient_id set of matching people.
    filter_qs = AdlRawRecord.all()
    if source_type:
        filter_qs = filter_qs.filter(source_type=source_type)
    if sex:
        filter_qs = filter_qs.filter(sex=sex)
    if alone:
        filter_qs = filter_qs.filter(alone=alone)
    if district:
        filter_qs = filter_qs.filter(district=district)
    if age_min is not None:
        filter_qs = filter_qs.filter(age__gte=age_min)
    if age_max is not None:
        filter_qs = filter_qs.filter(age__lte=age_max)
    if q:
        filter_qs = filter_qs.filter(care_recipient_id__icontains=q)

    matching_ids: set[str] = set(
        cast(
            list[str],
            await filter_qs.distinct().values_list("care_recipient_id", flat=True),
        )
    )

    if not matching_ids:
        return SuccessResponse(
            data=AdlRawRecipientsData(items=[], total=0, page=page, page_size=page_size)
        )

    # Pass 2 — gather full history rows for those people (filters NOT reapplied,
    # so per-person counts reflect each person's entire history).
    aggregate_rows = await AdlRawRecord.filter(care_recipient_id__in=matching_ids).only(
        *_AGGREGATE_FIELDS
    )

    grouped: dict[str, list[AdlRawRecord]] = defaultdict(list)
    for row in aggregate_rows:
        grouped[row.care_recipient_id].append(row)

    items: list[AdlRawRecipientItem] = []
    for rid, rows in grouped.items():
        # Demographics from the row with the most recent lifeog_date (deterministic).
        rep = max(rows, key=lambda r: (r.lifeog_date or date.min, r.id))
        type_counts = Counter(r.source_type for r in rows)
        all_dates = [
            d
            for r in rows
            for d in (r.lifeog_date, r.emergency_date, r.death_date)
            if d is not None
        ]
        items.append(
            AdlRawRecipientItem(
                care_recipient_id=rid,
                age=rep.age,
                sex=rep.sex,
                alone=rep.alone,
                district=rep.district,
                total_records=len(rows),
                source_type_counts=dict(type_counts),
                last_event_date=max(all_dates) if all_dates else None,
                first_event_date=min(all_dates) if all_dates else None,
            )
        )

    # Sort: most recent event first, then id ascending for tie-break.
    items.sort(
        key=lambda i: (
            -(i.last_event_date.toordinal() if i.last_event_date else 0),
            i.care_recipient_id,
        )
    )
    total = len(items)

    start = (page - 1) * page_size
    items = items[start : start + page_size]

    return SuccessResponse(
        data=AdlRawRecipientsData(items=items, total=total, page=page, page_size=page_size)
    )


@router.get(
    "/recipients/{recipient_id}/records",
    response_model=SuccessResponse[AdlRawRecipientRecordsData],
)
async def list_recipient_records(
    recipient_id: str = Path(..., min_length=1),
) -> SuccessResponse[AdlRawRecipientRecordsData]:
    rows = (
        await AdlRawRecord.filter(care_recipient_id=recipient_id)
        .only(*_RECORD_SUMMARY_FIELDS)
        .order_by("-lifeog_date", "-id")
    )

    if not rows:
        raise HTTPException(
            status_code=404, detail="해당 수급자의 ADL 원시 레코드를 찾을 수 없습니다."
        )

    items = [AdlRawRecordSummary.model_validate(r) for r in rows]
    return SuccessResponse(
        data=AdlRawRecipientRecordsData(care_recipient_id=recipient_id, items=items)
    )


@router.get("/{record_id}", response_model=SuccessResponse[AdlRawDetail])
async def get_adl_raw_detail(
    record_id: int = Path(..., ge=1),
) -> SuccessResponse[AdlRawDetail]:
    record = await AdlRawRecord.get_or_none(id=record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="ADL 원시 레코드를 찾을 수 없습니다.")

    outgoing_24h = aggregate_outgoing_to_24h(record.outgoing_1_list)
    sleep_depth_24h = aggregate_sleep_depth_to_24h(record.sleep_depth_1_list)
    outgoing_count_clean = recount_outgoing_count_d(record.outgoing_1_list)

    detail = AdlRawDetail(
        id=record.id,
        source_type=record.source_type,
        care_recipient_id=record.care_recipient_id,
        age=record.age,
        sex=record.sex,
        alone=record.alone,
        vision=record.vision,
        hearing=record.hearing,
        dosage=record.dosage,
        district=record.district,
        house_structure=record.house_structure,
        room_no=record.room_no,
        bath_location=record.bath_location,
        lifeog_date=record.lifeog_date,
        emergency_date=record.emergency_date,
        emergency_record=record.emergency_record,
        occurrence_place=record.occurrence_place,
        on_site=record.on_site,
        hospital_transfer=record.hospital_transfer,
        hospital_treatment=record.hospital_treatment,
        death_date=record.death_date,
        death_record=record.death_record,
        aix_d=record.aix_d,
        aix_1_eq_0_repeat_count=record.aix_1_eq_0_repeat_count,
        total_aix_sum=record.total_aix_sum,
        total_aix_inc_ratio=record.total_aix_inc_ratio,
        night_aix_ratio=record.night_aix_ratio,
        total_age_aix_ratio=record.total_age_aix_ratio,
        sleep_start_time_d=record.sleep_start_time_d,
        sleep_end_time_d=record.sleep_end_time_d,
        total_sleep_period=record.total_sleep_period,
        total_sleep_aix_ratio=record.total_sleep_aix_ratio,
        bath_count_d=record.bath_count_d,
        bath_time_d=record.bath_time_d,
        bath_nomove_time=record.bath_nomove_time,
        bath_count_in_sleep=record.bath_count_in_sleep,
        bath_time_per_count=record.bath_time_per_count,
        total_bath_average_count=record.total_bath_average_count,
        outgoing_count_d=outgoing_count_clean
        if outgoing_count_clean is not None
        else record.outgoing_count_d,
        outgoing_time_d=record.outgoing_time_d,
        outgoing_late_night_count_d=record.outgoing_late_night_count_d,
        outgoing_late_night_time_d=record.outgoing_late_night_time_d,
        last_outgoing_time=record.last_outgoing_time,
        total_outgoing_average_time=record.total_outgoing_average_time,
        total_outgoing_average_count=record.total_outgoing_average_count,
        aix_h_list=record.aix_h_list,
        temp_list=record.temp_list,
        humi_list=record.humi_list,
        illu_list=record.illu_list,
        outgoing_24h=outgoing_24h,
        sleep_depth_24h=sleep_depth_24h,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )

    return SuccessResponse(data=detail)
