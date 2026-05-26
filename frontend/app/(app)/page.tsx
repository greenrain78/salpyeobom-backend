"use client";

import Link from "next/link";
import { ArrowRight, Activity, Users } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboardSummary } from "@/lib/queries";

export default function DashboardPage() {
  const { data, isLoading, isError, error } = useDashboardSummary();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">대시보드</h1>
        <p className="text-sm text-muted-foreground">전체 모니터링 현황 요약입니다.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4 text-muted-foreground" />총 모니터링 인원
            </CardTitle>
            <CardDescription>현재 등록된 대상자 수</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-9 w-24" />
            ) : isError ? (
              <p className="text-sm text-destructive">{error?.message ?? "조회 실패"}</p>
            ) : (
              <p className="text-3xl font-semibold tabular-nums">
                {data?.total_monitoring_count.toLocaleString()}
                <span className="ml-1 text-base font-normal text-muted-foreground">명</span>
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4 text-muted-foreground" />빠른 이동
            </CardTitle>
            <CardDescription>주요 화면으로 바로 이동</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Link
              href="/patients"
              className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-secondary"
            >
              환자 목록 보기 <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
            <Link
              href="/situations"
              className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-secondary"
            >
              활성 상황 보기 <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
