import { Badge } from "@/components/ui/badge";
import type { ActionStatus } from "@/lib/types";

type StatusVariant = "warning" | "destructive" | "success" | "secondary";

const STATUS_VARIANT: Partial<Record<ActionStatus, StatusVariant>> = {
  "조치 대기": "warning",
  "현장 출동": "destructive",
  "조치 완료": "success",
};

export function StatusBadge({ status }: { status: string }) {
  const variant: StatusVariant = STATUS_VARIANT[status as ActionStatus] ?? "secondary";
  return <Badge variant={variant}>{status}</Badge>;
}
