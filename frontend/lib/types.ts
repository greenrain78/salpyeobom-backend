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
