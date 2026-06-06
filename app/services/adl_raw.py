"""adl_raw 라우터의 비즈니스 로직 — 필터 구성과 인메모리 집계/그룹핑/정렬.

라우터는 HTTP 입출력만 담당하고, 쿼리 필터 적용과 레코드 집계는 여기로 위임한다
(CLAUDE.md 레이어 규칙). 순수 함수는 DB 없이 단위 테스트할 수 있다.
"""

from collections import Counter, defaultdict
from datetime import date

from tortoise.queryset import QuerySet

from app.models.adl_raw import AdlRawRecord
from app.schemas.adl_raw import AdlRawRecipientItem


def apply_adl_filters(
    qs: QuerySet[AdlRawRecord],
    *,
    source_type: str | None = None,
    sex: str | None = None,
    alone: str | None = None,
    district: str | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    q: str | None = None,
) -> QuerySet[AdlRawRecord]:
    """요청 파라미터를 AdlRawRecord 쿼리셋에 적용. 목록/사람-그룹 엔드포인트 공통."""
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
    return qs


def summarize_list_aggregates(rows: list[AdlRawRecord]) -> tuple[dict[str, int], int]:
    """목록 응답 메타 — source_type 별 건수와 고유 수급자 수."""
    source_type_counts = dict(Counter(r.source_type for r in rows))
    unique_recipient_count = len({r.care_recipient_id for r in rows})
    return source_type_counts, unique_recipient_count


def build_recipient_items(rows: list[AdlRawRecord]) -> list[AdlRawRecipientItem]:
    """수급자(care_recipient_id) 단위로 묶어 인적 정보+카운트를 집계하고 최신 이벤트순 정렬.

    인적 정보는 가장 최근 lifeog_date 행에서 가져온다(동률 시 id 큰 쪽 — 결정적).
    카운트는 전달된 행 전체 기준이므로, 호출부는 한 사람의 전체 이력을 넘겨야 한다.
    """
    grouped: dict[str, list[AdlRawRecord]] = defaultdict(list)
    for row in rows:
        grouped[row.care_recipient_id].append(row)

    items: list[AdlRawRecipientItem] = []
    for rid, person_rows in grouped.items():
        rep = max(person_rows, key=lambda r: (r.lifeog_date or date.min, r.id))
        type_counts = Counter(r.source_type for r in person_rows)
        all_dates = [
            d
            for r in person_rows
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
                total_records=len(person_rows),
                source_type_counts=dict(type_counts),
                last_event_date=max(all_dates) if all_dates else None,
                first_event_date=min(all_dates) if all_dates else None,
            )
        )

    items.sort(
        key=lambda i: (
            -(i.last_event_date.toordinal() if i.last_event_date else 0),
            i.care_recipient_id,
        )
    )
    return items
