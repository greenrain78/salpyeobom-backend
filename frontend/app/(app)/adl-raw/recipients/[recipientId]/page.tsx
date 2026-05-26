"use client";

import { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAdlRawRecipients,
  useAdlRawRecordsForRecipient,
} from "@/lib/queries";
import type { AdlRawRecordSummary } from "@/lib/types";
import { ApiError } from "@/lib/api";

function sourceTypeBadgeVariant(
  sourceType: string,
): "destructive" | "secondary" | "outline" | "default" {
  if (sourceType === "응급") return "destructive";
  if (sourceType === "사망") return "secondary";
  return "outline";
}

function getOccurrenceDate(row: AdlRawRecordSummary): string {
  return row.lifeog_date ?? row.emergency_date ?? row.death_date ?? "—";
}

function formatRatio(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default function RecipientProfilePage() {
  const params = useParams<{ recipientId: string }>();
  const router = useRouter();
  const recipientId = decodeURIComponent(params.recipientId);

  const { data: recordsData, isLoading, error } =
    useAdlRawRecordsForRecipient(recipientId);

  // Reuse the recipient summary from the list query cache (no extra round trip).
  // If user lands directly on this page (no cache), we still have records' breakdown.
  const recordsItems = useMemo<AdlRawRecordSummary[]>(
    () => recordsData?.items ?? [],
    [recordsData?.items],
  );

  const summary = useMemo(() => {
    if (recordsItems.length === 0) return null;
    const typeCounts: Record<string, number> = {};
    const dates: string[] = [];
    for (const r of recordsItems) {
      typeCounts[r.source_type] = (typeCounts[r.source_type] ?? 0) + 1;
      for (const d of [r.lifeog_date, r.emergency_date, r.death_date]) {
        if (d) dates.push(d);
      }
    }
    dates.sort();
    return {
      typeCounts,
      total: recordsItems.length,
      firstDate: dates[0] ?? null,
      lastDate: dates[dates.length - 1] ?? null,
    };
  }, [recordsItems]);

  // Fallback demographics from the cached list query (if available).
  const { data: recipientsList } = useAdlRawRecipients({
    filters: {},
    page: 1,
    pageSize: 200,
  });
  const personMeta = recipientsList?.items.find(
    (it) => it.care_recipient_id === recipientId,
  );

  const isApiError = error instanceof ApiError;
  const notFound = isApiError && (error as ApiError).status === 404;

  return (
    <div className="space-y-4">
      {/* ── Header / back ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          사람 목록
        </Button>
        <div className="text-xs text-muted-foreground">
          수급자 ID: <span className="font-mono">{recipientId}</span>
        </div>
      </div>

      {notFound ? (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            이 수급자에 대한 ADL 원시 레코드를 찾을 수 없습니다.
          </CardContent>
        </Card>
      ) : (
        <>
          {/* ── Profile card ──────────────────────────────────────────────── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">수급자 프로필</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                  <ProfileItem label="나이" value={personMeta?.age ?? "—"} />
                  <ProfileItem label="성별" value={personMeta?.sex ?? "—"} />
                  <ProfileItem label="독거" value={personMeta?.alone ?? "—"} />
                  <ProfileItem
                    label="지역"
                    value={personMeta?.district ?? "—"}
                  />
                  <ProfileItem
                    label="총 레코드"
                    value={summary?.total ?? "—"}
                  />
                  <ProfileItem
                    label="관찰 기간"
                    value={
                      summary?.firstDate && summary?.lastDate
                        ? `${summary.firstDate} ~ ${summary.lastDate}`
                        : "—"
                    }
                  />
                  <div className="col-span-2 space-y-1">
                    <div className="text-xs text-muted-foreground">
                      이벤트 분포
                    </div>
                    {summary && Object.keys(summary.typeCounts).length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(summary.typeCounts).map(
                          ([type, count]) => (
                            <Badge
                              key={type}
                              variant={sourceTypeBadgeVariant(type)}
                            >
                              {type} {count}
                            </Badge>
                          ),
                        )}
                      </div>
                    ) : (
                      <div className="text-sm">—</div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ── Date-by-date records table ────────────────────────────────── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">일자별 레코드</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>이벤트 타입</TableHead>
                    <TableHead>발생일자</TableHead>
                    <TableHead className="text-right">AIX(일)</TableHead>
                    <TableHead className="text-right">총 AIX 합</TableHead>
                    <TableHead className="text-right">야간 AIX 비율</TableHead>
                    <TableHead className="text-right">외출 횟수</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <TableRow key={`skel-${i}`}>
                          {Array.from({ length: 7 }).map((__, j) => (
                            <TableCell key={j}>
                              <Skeleton className="h-4 w-full" />
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    : recordsItems.length === 0
                      ? (
                        <TableRow>
                          <TableCell
                            colSpan={7}
                            className="py-8 text-center text-sm text-muted-foreground"
                          >
                            이 사람의 레코드가 없습니다.
                          </TableCell>
                        </TableRow>
                      )
                      : recordsItems.map((row) => (
                          <TableRow
                            key={row.id}
                            className="cursor-pointer hover:bg-accent"
                            onClick={() => router.push(`/adl-raw/${row.id}`)}
                          >
                            <TableCell className="font-mono text-xs">
                              {row.id}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={sourceTypeBadgeVariant(row.source_type)}
                              >
                                {row.source_type}
                              </Badge>
                            </TableCell>
                            <TableCell>{getOccurrenceDate(row)}</TableCell>
                            <TableCell className="text-right">
                              {row.aix_d?.toFixed(2) ?? "—"}
                            </TableCell>
                            <TableCell className="text-right">
                              {row.total_aix_sum?.toFixed(1) ?? "—"}
                            </TableCell>
                            <TableCell className="text-right">
                              {formatRatio(row.night_aix_ratio)}
                            </TableCell>
                            <TableCell className="text-right">
                              {row.outgoing_count_d ?? "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function ProfileItem({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm">{value}</div>
    </div>
  );
}
