import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiRequest, apiRequestEnvelope } from "./api";
import type {
  ActionRequest,
  ActionResponse,
  ActiveSituationsData,
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
