"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import { useSubmitAction } from "@/lib/queries";
import type { ActionStatus, ActionType, SituationOut } from "@/lib/types";

const ACTION_TYPES: ActionType[] = ["유선 연락", "현장 출동", "기타"];
const STATUS_OPTIONS: ActionStatus[] = ["조치 대기", "현장 출동", "조치 완료"];

const schema = z.object({
  action_type: z.enum(["유선 연락", "현장 출동", "기타"]),
  action_note: z.string().optional(),
  status_update: z.enum(["조치 대기", "현장 출동", "조치 완료"]),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  situation: SituationOut | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ActionDialog({ situation, open, onOpenChange }: Props) {
  const submit = useSubmitAction();

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      action_type: "유선 연락",
      action_note: "",
      status_update: "조치 완료",
    },
  });

  useEffect(() => {
    if (open) {
      reset({
        action_type: "유선 연락",
        action_note: "",
        status_update: "조치 완료",
      });
    }
  }, [open, reset]);

  const onSubmit = handleSubmit(async (values) => {
    if (!situation) return;
    try {
      const res = await submit.mutateAsync({
        situationId: situation.situation_id,
        body: {
          action_type: values.action_type,
          action_note: values.action_note?.trim() || null,
          status_update: values.status_update,
        },
      });
      toast.success(res.message);
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "조치 등록에 실패했습니다.";
      toast.error(message);
    }
  });

  const actionType = watch("action_type");
  const statusUpdate = watch("status_update");
  const submitting = submit.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>조치 등록</DialogTitle>
          <DialogDescription>
            {situation ? `${situation.name} · ${situation.category}` : ""}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>조치 유형</Label>
            <Select
              value={actionType}
              onValueChange={(v) => setValue("action_type", v as ActionType, { shouldValidate: true })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ACTION_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.action_type && (
              <p className="text-xs text-destructive">{errors.action_type.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="action_note">메모 (선택)</Label>
            <Textarea
              id="action_note"
              placeholder="조치 내용을 자유롭게 기록"
              disabled={submitting}
              {...register("action_note")}
            />
          </div>

          <div className="space-y-1.5">
            <Label>상황 상태 업데이트</Label>
            <Select
              value={statusUpdate}
              onValueChange={(v) => setValue("status_update", v as ActionStatus, { shouldValidate: true })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.status_update && (
              <p className="text-xs text-destructive">{errors.status_update.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)} disabled={submitting}>
              취소
            </Button>
            <Button type="submit" disabled={submitting || !situation}>
              {submitting ? "등록 중…" : "등록"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
