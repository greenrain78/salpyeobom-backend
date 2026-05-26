"use client";

import Link from "next/link";
import { use } from "react";
import { ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePatientDetail } from "@/lib/queries";
import { ApiError } from "@/lib/api";

interface PageProps {
  params: Promise<{ patientId: string }>;
}

export default function PatientDetailPage({ params }: PageProps) {
  const { patientId } = use(params);
  const { data, isLoading, isError, error } = usePatientDetail(patientId);

  return (
    <div className="space-y-4">
      <Button asChild variant="ghost" size="sm">
        <Link href="/patients">
          <ArrowLeft className="mr-1 h-4 w-4" /> 목록으로
        </Link>
      </Button>

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : isError ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-destructive">
            {error instanceof ApiError && error.status === 404
              ? "대상자를 찾을 수 없습니다."
              : error?.message ?? "조회 실패"}
          </CardContent>
        </Card>
      ) : data ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">{data.name}</CardTitle>
              <CardDescription>{data.age}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div>
                <span className="text-muted-foreground">주소: </span>
                {data.address_full}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">행정 정보</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground">담당자</p>
                  <p className="font-medium">{data.administration.manager_name ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">관리 등급</p>
                  <p className="font-medium">{data.administration.management_level ?? "—"}</p>
                </div>
              </div>
              <div>
                <p className="mb-1.5 text-xs text-muted-foreground">질환</p>
                {data.administration.diseases.length === 0 ? (
                  <p className="text-sm text-muted-foreground">등록된 질환 없음</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {data.administration.diseases.map((d) => (
                      <Badge key={d} variant="secondary">
                        {d}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
