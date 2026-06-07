# ADL 합성데이터 생성 파이프라인

`/goal` 시나리오 기반 합성데이터 생성기 구현. 평시·응급·사망 3-클래스 분류기 학습용
`adl_raw_records` 행을 생성한다. 모든 정량 분포는 실데이터 **id 1~60**(응급 1명·사망 1명,
각 30일)에서만 도출했다. 설계 배경은 [`docs/synthetic-data-plan.md`](../../docs/synthetic-data-plan.md).

## 파이프라인

```
scenario_gen.py  ─▶  서사·페르소나·60일 일과표(daily)        [LLM 역할: 무엇이 일어났는가]
expander.py      ─▶  daily → 1440 배열 + 24 배열 + 스칼라    [코드: 클래스 분포 내 정량값]
run_batch.py     ─▶  N명/클래스 일괄 생성 → JSONL 또는 DB
validate_batch.py─▶  실 vs 합성 분포 비교 (KS + 클래스 분리도)
```

`scenario_gen` 은 클래스 *안*의 변주(활동 형태·이벤트·외출/목욕 유무·추세)만 정하고,
`expander` 가 클래스 경계(시그니처)를 강제한다 — 사망 목욕 0, night_aix 봉투, aix 33배수
양자화, outgoing 254/255 sentinel, sleep_depth 0~4.

## 사용법

```bash
# 1) 단건 생성 (검토용)
uv run python scripts/synthetic/scenario_gen.py            # 클래스별 1명씩 → out/synthetic/*.json
uv run python scripts/synthetic/scenario_gen.py 응급 7     # 특정 클래스·시드

# 2) 대량 생성
uv run python scripts/synthetic/run_batch.py --per-class 25                 # 샘플 4,500행
uv run python scripts/synthetic/run_batch.py --per-class 1000               # 전체 180,000행 → JSONL

# 원격 DB 적재(신중히 — .env 의 DATABASE_URL=원격 사용). 권장: JSONL 을 먼저 만들고 그 파일을
# 적재해 '파일=DB' 를 보장. --skip-lines 로 이미 적재된 앞부분 재적재 방지.
uv run python scripts/synthetic/run_batch.py --sink db --from-jsonl out/synthetic/batch.jsonl
#   (생성+즉시 적재도 가능: --sink db --per-class 1000  / DB URL 직접 지정: --db-url postgres://...)

# 3) 검증
uv run python scripts/synthetic/validate_batch.py --batch out/synthetic/batch.jsonl
```

## 클래스 시그니처 (실측 → 합성 재현)

| 지표 | 평시(외삽) | 응급 | 사망 |
|------|-----------|------|------|
| `bath_count_d` | 3~20 | 4~48 | **0 (불변)** |
| `night_aix_ratio` | <60 | 0~20417 (수천, 종반 급등) | 0~15 |
| `aix_d` | ~50 | ~64 (종반 300+ 급등) | ~181 (전구간 고값) |
| `total_sleep_period` | 280~520 | 0~719 | 0~662 (40% 정확히 0) |
| `outgoing_count_d` | 3~16 | 3~16 (점감) | 0~9 |

## 검증 결과 (샘플 25명/클래스 vs 실 id1~60)

- **평균·범위**: 12개 주요 지표 모두 실측과 거의 일치
- **클래스 분리도**: 사망 목욕=0 100%, 응급 night_aix 수천 대 사망/평시 한 자릿수 — 결정축 보존
- **KS(n-매칭)**: 8~9/12 지표 p>0.05. 기각된 지표(night_aix 응급 등)는 실데이터가 1인·30일
  자기상관 시계열이라 모집단 생성기로 정확한 CDF 일치가 불가능·불필요 — 위치/척도와
  분리 시그니처는 일치한다.

## 데이터 품질 함정 재현 (학습용 노이즈 유지)

실데이터(`docs/database-schema.md` §3.4)의 구조적 노이즈를 의도적으로 재현한다:
- `outgoing_1_list` 거의 254/255 sentinel (실제 외출코드 부재)
- `sleep_depth_1_list` 사망 클래스 전부 None (원본 결측)
- `sleep_start_time_d`/`sleep_end_time_d` 분-int 문자열 (`"1380"`)
- `place_code` 분포 클래스별 상이 (응급 {254,0,20,1,255} / 사망 {30,10,254,255})

## 산출물

- `out/synthetic/{평시,응급,사망}_seed*.json` — 단건 일과표(검토용)
- `out/synthetic/batch.jsonl` — 대량 생성 행 (1행 = adl_raw_records 1행, JSON)
- `care_recipient_id` 접두사 `SYN-` 로 합성 식별 (실데이터와 구분)
