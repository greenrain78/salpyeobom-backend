"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/status-badge";
import { ActionDialog } from "@/components/action-dialog";
import { useActiveSituations } from "@/lib/queries";
import type { SituationOut } from "@/lib/types";

export default function SituationsPage() {
  const { data, isLoading, isError, error } = useActiveSituations(20);
  const [active, setActive] = useState<SituationOut | null>(null);
  const [open, setOpen] = useState(false);

  const handleOpen = (s: SituationOut) => {
    setActive(s);
    setOpen(true);
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">활성 상황</h1>
        <p className="text-sm text-muted-foreground">조치가 완료되지 않은 상황을 최근순으로 보여줍니다.</p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-destructive">
            {error?.message ?? "상황을 불러오지 못했습니다."}
          </CardContent>
        </Card>
      ) : data && data.situations.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            현재 활성 상황이 없습니다.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {data?.situations.map((s) => (
            <Card key={s.situation_id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Badge variant="outline">{s.category}</Badge>
                      <Link
                        href={`/patients/${encodeURIComponent(s.patient_id)}`}
                        className="hover:underline"
                      >
                        {s.name}
                      </Link>
                      <span className="text-xs font-normal text-muted-foreground">
                        {s.occurred_at}
                      </span>
                    </CardTitle>
                    <CardDescription>{s.address_summary}</CardDescription>
                  </div>
                  <StatusBadge status={s.action_status} />
                </div>
              </CardHeader>
              <CardContent className="flex items-end justify-between gap-3 pt-2">
                <p className="text-sm text-muted-foreground">
                  {s.detail_reason ?? "추가 설명 없음"}
                </p>
                <Button size="sm" onClick={() => handleOpen(s)}>
                  조치 등록
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ActionDialog situation={active} open={open} onOpenChange={setOpen} />
    </div>
  );
}
