// Mirrors app/schemas/*.py — keep in sync if backend contract changes.

export interface UserOut {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface DashboardSummary {
  total_monitoring_count: number;
}

export interface PatientListItem {
  patient_id: string;
  name: string;
  address_summary: string;
  manager_name: string | null;
}

export interface PatientListData {
  total_count: number;
  current_page: number;
  total_pages: number;
  patients: PatientListItem[];
}

export interface Administration {
  manager_name: string | null;
  management_level: string | null;
  diseases: string[];
}

export interface PatientDetail {
  name: string;
  age: string;
  address_full: string;
  administration: Administration;
}

export interface SituationOut {
  situation_id: number;
  patient_id: string;
  name: string;
  address_summary: string;
  category: string;
  detail_reason: string | null;
  occurred_at: string;
  // 백엔드는 str로 응답한다. 알려진 값은 ActionStatus 와 일치하지만
  // 임의 문자열도 들어올 수 있으므로 union 으로 강제하지 않는다.
  action_status: string;
}

export interface ActiveSituationsData {
  situations: SituationOut[];
}

export type ActionType = "유선 연락" | "현장 출동" | "기타";
export type ActionStatus = "조치 대기" | "현장 출동" | "조치 완료";

export interface ActionRequest {
  action_type: ActionType;
  action_note?: string | null;
  status_update: ActionStatus;
}

export interface ActionResponse {
  status: "success";
  message: string;
}

export interface SuccessEnvelope<T> {
  status: "success";
  data: T;
}

export interface ErrorEnvelope {
  status: "error";
  message: string | string[];
}

// ADL Raw Records 분석 페이지 — backend app/schemas/adl_raw.py 미러

// 사람-그룹 목록: 1행 = 1명 (care_recipient_id 기준)
export interface AdlRawRecipientItem {
  care_recipient_id: string;
  age: number | null;
  sex: string | null;
  alone: string | null;
  district: string | null;
  total_records: number;
  source_type_counts: Record<string, number>;
  last_event_date: string | null;
  first_event_date: string | null;
}

export interface AdlRawRecipientsData {
  items: AdlRawRecipientItem[];
  total: number;
  page: number;
  page_size: number;
}

// 한 사람의 일자별 레코드 요약 (시계열 배열 제외)
export interface AdlRawRecordSummary {
  id: number;
  source_type: string;
  lifeog_date: string | null;
  emergency_date: string | null;
  death_date: string | null;
  aix_d: number | null;
  total_aix_sum: number | null;
  night_aix_ratio: number | null;
  outgoing_count_d: number | null;
}

export interface AdlRawRecipientRecordsData {
  care_recipient_id: string;
  items: AdlRawRecordSummary[];
}

export interface AdlRawDetail {
  id: number;
  source_type: string;
  care_recipient_id: string;
  age: number | null;
  sex: string | null;
  alone: string | null;
  vision: string | null;
  hearing: string | null;
  dosage: string | null;
  district: string | null;
  house_structure: string | null;
  room_no: number | null;
  bath_location: string | null;
  lifeog_date: string | null;
  emergency_date: string | null;
  emergency_record: string | null;
  occurrence_place: string | null;
  on_site: string | null;
  hospital_transfer: string | null;
  hospital_treatment: string | null;
  death_date: string | null;
  death_record: string | null;
  aix_d: number | null;
  aix_1_eq_0_repeat_count: number | null;
  total_aix_sum: number | null;
  total_aix_inc_ratio: number | null;
  night_aix_ratio: number | null;
  total_age_aix_ratio: number | null;
  sleep_start_time_d: string | null;
  sleep_end_time_d: string | null;
  total_sleep_period: number | null;
  total_sleep_aix_ratio: number | null;
  bath_count_d: number | null;
  bath_time_d: number | null;
  bath_nomove_time: number | null;
  bath_count_in_sleep: number | null;
  bath_time_per_count: number | null;
  total_bath_average_count: number | null;
  outgoing_count_d: number | null;
  outgoing_time_d: number | null;
  outgoing_late_night_count_d: number | null;
  outgoing_late_night_time_d: number | null;
  last_outgoing_time: string | null;
  total_outgoing_average_time: number | null;
  total_outgoing_average_count: number | null;
  aix_h_list: number[] | null;
  temp_list: number[] | null;
  humi_list: number[] | null;
  illu_list: number[] | null;
  outgoing_24h: number[] | null;
  sleep_depth_24h: number[] | null;
  created_at: string;
}

export interface AdlRawFilters {
  source_type?: string;
  sex?: string;
  alone?: string;
  district?: string;
  age_min?: number;
  age_max?: number;
  q?: string;
}
