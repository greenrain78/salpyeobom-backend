import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiRequest, apiRequestEnvelope } from "./api";
import type {
  ActionRequest,
  ActionResponse,
  ActiveSituationsData,
  AdlRawDetail,
  AdlRawFilters,
  AdlRawRecipientRecordsData,
  AdlRawRecipientsData,
  DashboardSummary,
  PatientDetail,
  PatientListData,
} from "./types";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => apiRequestEnvelope<DashboardSummary>("/api/v1/dashboard/summary"),
  });
}

interface UsePatientsArgs {
  page: number;
  limit: number;
  searchName?: string;
}

export function usePatients({ page, limit, searchName }: UsePatientsArgs) {
  return useQuery({
    queryKey: ["patients", { page, limit, searchName: searchName ?? "" }],
    queryFn: () =>
      apiRequestEnvelope<PatientListData>("/api/v1/patients", {
        searchParams: { page, limit, search_name: searchName ?? undefined },
      }),
    placeholderData: (prev) => prev,
  });
}

export function usePatientDetail(patientId: string | undefined) {
  return useQuery({
    queryKey: ["patient", patientId],
    queryFn: () =>
      apiRequestEnvelope<PatientDetail>(
        `/api/v1/patients/${encodeURIComponent(patientId ?? "")}/details`
      ),
    enabled: Boolean(patientId),
  });
}

export function useActiveSituations(limit = 20) {
  return useQuery({
    queryKey: ["situations", "active", limit],
    queryFn: () =>
      apiRequestEnvelope<ActiveSituationsData>("/api/v1/situations/active", {
        searchParams: { limit },
      }),
  });
}

interface SubmitActionArgs {
  situationId: number;
  body: ActionRequest;
}

export function useSubmitAction() {
  const qc = useQueryClient();
  return useMutation<ActionResponse, ApiError, SubmitActionArgs>({
    mutationFn: ({ situationId, body }) =>
      apiRequest<ActionResponse>(`/api/v1/situations/${situationId}/actions`, {
        method: "POST",
        body,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["situations"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

interface UseAdlRawRecipientsArgs {
  filters: AdlRawFilters;
  page: number;
  pageSize: number;
}

export function useAdlRawRecipients({
  filters,
  page,
  pageSize,
}: UseAdlRawRecipientsArgs) {
  return useQuery({
    queryKey: ["adl-raw", "recipients", { filters, page, pageSize }],
    queryFn: () =>
      apiRequestEnvelope<AdlRawRecipientsData>("/api/v1/adl-raw/recipients", {
        searchParams: {
          source_type: filters.source_type,
          sex: filters.sex,
          alone: filters.alone,
          district: filters.district,
          age_min: filters.age_min,
          age_max: filters.age_max,
          q: filters.q,
          page,
          page_size: pageSize,
        },
      }),
    placeholderData: (prev) => prev,
  });
}

export function useAdlRawRecordsForRecipient(recipientId: string | undefined) {
  return useQuery({
    queryKey: ["adl-raw", "recipient-records", recipientId],
    queryFn: () =>
      apiRequestEnvelope<AdlRawRecipientRecordsData>(
        `/api/v1/adl-raw/recipients/${encodeURIComponent(recipientId ?? "")}/records`,
      ),
    enabled: Boolean(recipientId),
  });
}

export function useAdlRawDetail(id: number | undefined) {
  return useQuery({
    queryKey: ["adl-raw", "detail", id],
    queryFn: () => apiRequestEnvelope<AdlRawDetail>(`/api/v1/adl-raw/${id}`),
    enabled: id !== undefined,
  });
}
