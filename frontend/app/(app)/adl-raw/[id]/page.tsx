"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { useAdlRawDetail } from "@/lib/queries";
import { ApiError } from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

function fmt(val: number | string | null | undefined, fallback = "—"): string {
  if (val == null) return fallback;
  return String(val);
}

function fmtNum(val: number | null | undefined, decimals = 1): string {
  if (val == null) return "—";
  return val.toFixed(decimals);
}

function fmtPct(val: number | null | undefined): string {
  if (val == null) return "—";
  return `${(val * 100).toFixed(1)}%`;
}

/** Convert total minutes → "hh:mm" */
function fmtMinutes(val: number | null | undefined): string {
  if (val == null) return "—";
  const h = Math.floor(val / 60);
  const m = Math.round(val % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function sourceTypeBadgeVariant(
  src: string
): "destructive" | "secondary" | "outline" | "default" {
  if (src === "응급") return "destructive";
  if (src === "사망") return "secondary";
  return "outline";
}

interface KvRowProps {
  label: string;
  value: string | number | null | undefined;
}
function KvRow({ label, value }: KvRowProps) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value ?? "—"}</p>
    </div>
  );
}

interface ScalarCardProps {
  title: string;
  value: string;
}
function ScalarCard({ title, value }: ScalarCardProps) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}

interface SimpleLineChartProps {
  title: string;
  data: Array<{ hour: number; value: number | null }> | null;
  unit?: string;
  color?: string;
  dataKey?: string;
}
function SimpleLineChartCard({
  title,
  data,
  unit = "",
  color = "hsl(var(--chart-1))",
  dataKey = "value",
}: SimpleLineChartProps) {
  const config: ChartConfig = {
    [dataKey]: { label: title, color },
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {data == null || data.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
            데이터 없음
          </div>
        ) : (
          <ChartContainer config={config} className="h-[200px] w-full">
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="hour"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                tickFormatter={(v: number) => `${v}시`}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                unit={unit}
                width={unit ? 40 : 30}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelFormatter={(v) => `${v}시`}
                  />
                }
              />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </LineChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default function AdlRawDetailPage({ params }: PageProps) {
  const { id: idStr } = use(params);
  const id = parseInt(idStr, 10);
  const router = useRouter();

  const { data, isLoading, isError, error } = useAdlRawDetail(
    Number.isNaN(id) ? undefined : id
  );

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  // ── Error / 404 ────────────────────────────────────────────────────────────
  if (isError || !data) {
    const is404 = error instanceof ApiError && error.status === 404;
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          목록으로
        </Button>
        <Card>
          <CardContent className="py-12 text-center text-sm text-destructive">
            {is404
              ? "레코드를 찾을 수 없습니다."
              : (error as Error)?.message ?? "조회 실패"}
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Chart data ─────────────────────────────────────────────────────────────
  const aixChartData =
    data.aix_h_list?.map((value, hour) => ({ hour, value })) ?? null;
  const outgoingChartData =
    data.outgoing_24h?.map((value, hour) => ({ hour, value })) ?? null;
  const sleepChartData =
    data.sleep_depth_24h?.map((value, hour) => ({ hour, value })) ?? null;
  const tempChartData =
    data.temp_list?.map((value, hour) => ({ hour, value })) ?? null;
  const humiChartData =
    data.humi_list?.map((value, hour) => ({ hour, value })) ?? null;
  const illuChartData =
    data.illu_list?.map((value, hour) => ({ hour, value })) ?? null;

  return (
    <div className="space-y-5">
      {/* ── Back button ──────────────────────────────────────────────────────── */}
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-1 h-4 w-4" />
        목록으로
      </Button>

      {/* ── Profile card ─────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            수급자 프로필{" "}
            <span className="font-mono text-sm font-normal text-muted-foreground">
              #{data.id}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-4">
            <KvRow label="나이" value={data.age} />
            <KvRow label="성별" value={data.sex} />
            <KvRow label="독거" value={data.alone} />
            <KvRow label="지역" value={data.district} />
            <KvRow label="주거 형태" value={data.house_structure} />
            <KvRow label="복약 여부" value={data.dosage} />
            <KvRow label="시력" value={data.vision} />
            <KvRow label="청력" value={data.hearing} />
            <KvRow label="호실 번호" value={data.room_no} />
            <KvRow label="욕실 위치" value={data.bath_location} />
            <KvRow label="발생 장소" value={data.occurrence_place} />
          </div>
        </CardContent>
      </Card>

      {/* ── Event card ───────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">이벤트 정보</CardTitle>
            <Badge variant={sourceTypeBadgeVariant(data.source_type)}>
              {data.source_type}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <KvRow label="평소 일자" value={data.lifeog_date} />
            <KvRow label="응급 일자" value={data.emergency_date} />
            <KvRow label="사망 일자" value={data.death_date} />
          </div>
          {data.emergency_record && (
            <div>
              <p className="text-xs text-muted-foreground">응급 기록</p>
              <p className="mt-1 rounded bg-muted p-2 text-xs leading-relaxed">
                {data.emergency_record}
              </p>
            </div>
          )}
          {data.death_record && (
            <div>
              <p className="text-xs text-muted-foreground">사망 기록</p>
              <p className="mt-1 rounded bg-muted p-2 text-xs leading-relaxed">
                {data.death_record}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Scalar metric cards (6) ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <ScalarCard title="총 AIX 합계" value={fmtNum(data.total_aix_sum, 1)} />
        <ScalarCard title="야간 AIX 비율" value={fmtPct(data.night_aix_ratio)} />
        <ScalarCard title="총 수면 시간" value={fmtMinutes(data.total_sleep_period)} />
        <ScalarCard title="입욕 횟수" value={fmt(data.bath_count_d)} />
        <ScalarCard title="외출 횟수" value={fmt(data.outgoing_count_d)} />
        <ScalarCard
          title="심야 외출 횟수"
          value={fmt(data.outgoing_late_night_count_d)}
        />
      </div>

      {/* ── Chart section ────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <h2 className="text-base font-semibold tracking-tight">24시간 시계열</h2>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Chart 1: AIX */}
          <SimpleLineChartCard
            title="AIX 24h"
            data={aixChartData}
            color="hsl(var(--chart-1))"
          />

          {/* Chart 2: 외출 */}
          <SimpleLineChartCard
            title="외출 24h"
            data={outgoingChartData}
            color="hsl(var(--chart-2))"
          />

          {/* Chart 3: 수면 깊이 */}
          <SimpleLineChartCard
            title="수면 깊이 24h 평균"
            data={sleepChartData}
            color="hsl(var(--chart-3))"
          />

          {/* Chart 4: 온도 */}
          <SimpleLineChartCard
            title="온도 24h (℃)"
            data={tempChartData}
            unit="℃"
            color="hsl(var(--chart-4))"
          />

          {/* Chart 5: 습도 */}
          <SimpleLineChartCard
            title="습도 24h (%)"
            data={humiChartData}
            unit="%"
            color="hsl(var(--chart-5))"
          />

          {/* Chart 6: 조도 */}
          <SimpleLineChartCard
            title="조도 24h (lux)"
            data={illuChartData}
            unit="lx"
            color="hsl(var(--chart-1))"
            dataKey="value"
          />
        </div>
      </div>
    </div>
  );
}
