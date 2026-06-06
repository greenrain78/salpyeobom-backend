"""도메인 범주형 값의 단일 출처(Single Source of Truth).

`StrEnum` 을 사용하므로 각 멤버는 그 자체로 문자열이다 (`str(ActionStatus.PENDING) == "조치 대기"`).
따라서 Tortoise `CharEnumField` 저장값, Pydantic `str` 필드 직렬화, 평문 문자열 비교가 모두
값 문자열 그대로 동작한다.

여기에 포함하지 않은 범주형 필드와 그 이유:
- `Situation.category` — 실제 사용값이 분기되어 있다. 문서상 분류("낙상 의심"·"미응답"·
  "이상 패턴"·"사망 감지") 외에 `scripts/seed_from_adl.py` 가 ADL 이벤트를 그대로 옮기며
  "응급"·"사망" 을 넣는다. 경계가 닫혀 있지 않아 ENUM 으로 강제하지 않는다.
- `AdlRawRecord.source_type` — 외부 CSV 적재에서 오는 개방형 값으로, 실데이터에
  "응급"·"사망" 외에 "평소"·"사망전" 이 이미 존재한다. 새 변형이 추가될 수 있어
  ENUM 으로 강제하면 기존 데이터 읽기까지 깨진다. 자유 문자열로 둔다.
- `Patient.management_level` — 선택적(nullable) 행정 메타데이터로 등급 체계가 가변적이다.
"""

from enum import StrEnum


class ActionStatus(StrEnum):
    """`Situation.action_status` — 조치 진행 상태.

    내부에서만 설정되며 값 집합이 닫혀 있어 ENUM 으로 강제한다.
    활성/비활성의 단일 출처: `COMPLETED` 가 아니면 활성으로 본다 ([[Situation.is_active]]).
    """

    PENDING = "조치 대기"
    DISPATCHED = "현장 출동"
    COMPLETED = "조치 완료"
