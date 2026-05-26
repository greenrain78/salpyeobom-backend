"use client";

import { useMemo, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdlRawRecipients } from "@/lib/queries";
import type { AdlRawFilters, AdlRawRecipientItem } from "@/lib/types";

const PAGE_SIZE = 50;
/** Sentinel for the "전체" Select option — Radix Select rejects "". Mapped to "" before URL serialization (buildQs drops empty strings). */
const ALL_VALUE = "__all__";

/** Build URLSearchParams, omitting undefined/empty-string values. */
function buildQs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") {
      sp.set(k, String(v));
    }
  }
  return sp.toString();
}

function sumValues(counts: Record<string, number> | undefined): number {
  if (!counts) return 0;
  return Object.values(counts).reduce((a, b) => a + b, 0);
}

function sourceTypeBadgeVariant(
  sourceType: string,
): "destructive" | "secondary" | "outline" | "default" {
  if (sourceType === "응급") return "destructive";
  if (sourceType === "사망") return "secondary";
  return "outline";
}

export default function AdlRawPage() {
  const sp = useSearchParams();
  const router = useRouter();

  // ── URL → derived state (single direction) ──────────────────────────────────
  const page = Number(sp.get("page") ?? "1");
  const filters: AdlRawFilters = useMemo(
    () => ({
      source_type: sp.get("source_type") || undefined,
      sex: sp.get("sex") || undefined,
      alone: sp.get("alone") || undefined,
      district: sp.get("district") || undefined,
      age_min: sp.get("age_min") ? Number(sp.get("age_min")) : undefined,
      age_max: sp.get("age_max") ? Number(sp.get("age_max")) : undefined,
      q: sp.get("q") || undefined,
    }),
    [sp],
  );

  // ── Local form state (text inputs — debounced before URL replace) ───────────
  const [district, setDistrict] = useState(sp.get("district") ?? "");
  const [ageMin, setAgeMin] = useState(sp.get("age_min") ?? "");
  const [ageMax, setAgeMax] = useState(sp.get("age_max") ?? "");
  const [q, setQ] = useState(sp.get("q") ?? "");

  // Keep local state in sync when URL is changed externally (back/forward).
  const prevSpRef = useRef(sp.toString());
  useEffect(() => {
    const next = sp.toString();
    if (next !== prevSpRef.current) {
      prevSpRef.current = next;
      setDistrict(sp.get("district") ?? "");
      setAgeMin(sp.get("age_min") ?? "");
      setAgeMax(sp.get("age_max") ?? "");
      setQ(sp.get("q") ?? "");
    }
  }, [sp]);

  // ── Debounce helper: 300ms for text inputs ──────────────────────────────────
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function pushTextFilters(overrides: Partial<Record<string, string>>) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const qs = buildQs({
        source_type: sp.get("source_type") ?? "",
        sex: sp.get("sex") ?? "",
        alone: sp.get("alone") ?? "",
        district: overrides.district ?? district,
        age_min: overrides.age_min ?? ageMin,
        age_max: overrides.age_max ?? ageMax,
        q: overrides.q ?? q,
        page: "1",
      });
      router.replace(`/adl-raw?${qs}`, { scroll: false });
    }, 300);
  }

  // ── Select handlers (immediate URL replace, no debounce) ────────────────────
  function handleSelectChange(key: "source_type" | "sex" | "alone", value: string) {
    const next = value === ALL_VALUE ? "" : value;
    const qs = buildQs({
      source_type: key === "source_type" ? next : (sp.get("source_type") ?? ""),
      sex: key === "sex" ? next : (sp.get("sex") ?? ""),
      alone: key === "alone" ? next : (sp.get("alone") ?? ""),
      district,
      age_min: ageMin,
      age_max: ageMax,
      q,
      page: "1",
    });
    router.replace(`/adl-raw?${qs}`, { scroll: false });
  }

  function goToPage(nextPage: number) {
    const qs = buildQs({
      source_type: sp.get("source_type") ?? "",
      sex: sp.get("sex") ?? "",
      alone: sp.get("alone") ?? "",
      district,
      age_min: ageMin,
      age_max: ageMax,
      q,
      page: nextPage,
    });
    router.replace(`/adl-raw?${qs}`, { scroll: false });
  }

  // ── Data ────────────────────────────────────────────────────────────────────
  const { data, isLoading, isFetching } = useAdlRawRecipients({
    filters,
    page,
    pageSize: PAGE_SIZE,
  });

  const totalPeople = data?.total ?? 0;
  const totalPages = totalPeople ? Math.ceil(totalPeople / PAGE_SIZE) : 1;
  const items = useMemo<AdlRawRecipientItem[]>(
    () => data?.items ?? [],
    [data?.items],
  );

  // Aggregate KPIs across the current filtered set of people.
  const allTypeCounts = useMemo(() => {
    const merged: Record<string, number> = {};
    for (const it of items) {
      for (const [k, v] of Object.entries(it.source_type_counts)) {
        merged[k] = (merged[k] ?? 0) + v;
      }
    }
    return merged;
  }, [items]);
  const totalRecordsAcrossPeople = useMemo(
    () => items.reduce((sum, it) => sum + it.total_records, 0),
    [items],
  );
  const avgRecordsPerPerson =
    items.length > 0
      ? (totalRecordsAcrossPeople / items.length).toFixed(1)
      : "—";

  return (
    <div className="space-y-4">
      {/* ── KPI row ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">
              필터링된 사람 수
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{totalPeople}</div>
            <div className="text-xs text-muted-foreground">
              표시 중 {items.length}명 / 총 {totalPeople}명
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">
              이벤트 타입별 건수 (현재 페이지 사람의 전체 이력 기준)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(allTypeCounts).length === 0 ? (
              <div className="text-2xl font-semibold">—</div>
            ) : (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                {Object.entries(allTypeCounts).map(([type, count]) => (
                  <Badge key={type} variant={sourceTypeBadgeVariant(type)}>
                    {type} {count}
                  </Badge>
                ))}
              </div>
            )}
            <div className="mt-1 text-xs text-muted-foreground">
              합계 {sumValues(allTypeCounts)}건
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">
              1인당 평균 레코드 수
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{avgRecordsPerPerson}</div>
            <div className="text-xs text-muted-foreground">
              표시 {items.length}명 기준
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Filter block ───────────────────────────────────────────────────── */}
      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">이벤트 타입</Label>
              <Select
                value={sp.get("source_type") ?? ALL_VALUE}
                onValueChange={(v) => handleSelectChange("source_type", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="전체" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_VALUE}>전체</SelectItem>
                  <SelectItem value="응급">응급</SelectItem>
                  <SelectItem value="사망">사망</SelectItem>
                  <SelectItem value="평소">평소</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">성별</Label>
              <Select
                value={sp.get("sex") ?? ALL_VALUE}
                onValueChange={(v) => handleSelectChange("sex", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="전체" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_VALUE}>전체</SelectItem>
                  <SelectItem value="M">M</SelectItem>
                  <SelectItem value="F">F</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">독거</Label>
              <Select
                value={sp.get("alone") ?? ALL_VALUE}
                onValueChange={(v) => handleSelectChange("alone", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="전체" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_VALUE}>전체</SelectItem>
                  <SelectItem value="Y">Y</SelectItem>
                  <SelectItem value="N">N</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">지역</Label>
              <Input
                value={district}
                onChange={(e) => {
                  setDistrict(e.target.value);
                  pushTextFilters({ district: e.target.value });
                }}
                placeholder="지역 검색"
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">나이대</Label>
              <div className="flex items-center gap-1">
                <Input
                  value={ageMin}
                  onChange={(e) => {
                    setAgeMin(e.target.value);
                    pushTextFilters({ age_min: e.target.value });
                  }}
                  placeholder="최소"
                  type="number"
                  min={0}
                  className="h-8 text-xs"
                />
                <span className="text-xs text-muted-foreground">~</span>
                <Input
                  value={ageMax}
                  onChange={(e) => {
                    setAgeMax(e.target.value);
                    pushTextFilters({ age_max: e.target.value });
                  }}
                  placeholder="최대"
                  type="number"
                  min={0}
                  className="h-8 text-xs"
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">수급자 검색</Label>
              <Input
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  pushTextFilters({ q: e.target.value });
                }}
                placeholder="수급자 ID"
                className="h-8 text-xs"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Recipient table ────────────────────────────────────────────────── */}
      <Card>
        <CardContent className="pt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>수급자 ID</TableHead>
                <TableHead>나이</TableHead>
                <TableHead>성별</TableHead>
                <TableHead>독거</TableHead>
                <TableHead>지역</TableHead>
                <TableHead>응급</TableHead>
                <TableHead>사망</TableHead>
                <TableHead>평소</TableHead>
                <TableHead>최근 이벤트일</TableHead>
                <TableHead className="text-right">총 레코드</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading || isFetching
                ? Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={`skel-${i}`}>
                      {Array.from({ length: 10 }).map((__, j) => (
                        <TableCell key={j}>
                          <Skeleton className="h-4 w-full" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                : items.length === 0
                  ? (
                    <TableRow>
                      <TableCell
                        colSpan={10}
                        className="py-8 text-center text-sm text-muted-foreground"
                      >
                        조건에 맞는 사람이 없습니다.
                      </TableCell>
                    </TableRow>
                  )
                  : items.map((row: AdlRawRecipientItem) => (
                      <TableRow
                        key={row.care_recipient_id}
                        className="cursor-pointer hover:bg-accent"
                        onClick={() =>
                          router.push(
                            `/adl-raw/recipients/${encodeURIComponent(row.care_recipient_id)}`,
                          )
                        }
                      >
                        <TableCell className="font-mono text-xs">
                          {row.care_recipient_id}
                        </TableCell>
                        <TableCell>{row.age ?? "—"}</TableCell>
                        <TableCell>{row.sex ?? "—"}</TableCell>
                        <TableCell>{row.alone ?? "—"}</TableCell>
                        <TableCell>{row.district ?? "—"}</TableCell>
                        <TableCell>
                          {row.source_type_counts["응급"] ?? 0}
                        </TableCell>
                        <TableCell>
                          {row.source_type_counts["사망"] ?? 0}
                        </TableCell>
                        <TableCell>
                          {row.source_type_counts["평소"] ?? 0}
                        </TableCell>
                        <TableCell>{row.last_event_date ?? "—"}</TableCell>
                        <TableCell className="text-right">
                          {row.total_records}
                        </TableCell>
                      </TableRow>
                    ))}
            </TableBody>
          </Table>

          {/* Pagination footer */}
          <div className="mt-3 flex items-center justify-end gap-2 text-xs text-muted-foreground">
            <span>
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => goToPage(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => goToPage(page + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
