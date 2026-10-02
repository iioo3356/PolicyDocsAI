"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X, LoaderCircle } from "lucide-react";
import { api, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function CreateProjectDialog({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const qc = useQueryClient();
  const create = useMutation({
    mutationFn: () => api<Project>("/projects", {
      method: "POST", body: JSON.stringify({ name: name.trim(), description: description.trim() }),
    }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["projects"] });
      onClose();
    },
  });
  useEffect(() => {
    const node = dialog.current;
    const previous = document.activeElement as HTMLElement | null;
    node?.showModal();
    nameInput.current?.focus();
    return () => { node?.close(); previous?.focus(); };
  }, []);
  function close() { if (!create.isPending) onClose(); }
  function submit(event: FormEvent) {
    event.preventDefault();
    if (name.trim() && !create.isPending) create.mutate();
  }
  return <dialog ref={dialog} className="project-dialog" aria-labelledby="create-project-title"
    aria-describedby="create-project-description"
    onCancel={event => { event.preventDefault(); close(); }}
    onClick={event => { if (event.target === event.currentTarget) close(); }}>
    <header className="project-dialog-header">
      <span className="section-eyebrow type-label">NEW WORKSPACE</span>
      <Button type="button" variant="ghost" size="icon" aria-label="프로젝트 생성 닫기" disabled={create.isPending} onClick={close}><X /></Button>
    </header>
    <h2 className="type-heading" id="create-project-title">새 프로젝트 만들기</h2>
    <p className="type-caption" id="create-project-description">서비스의 정책과 근거를 정리할 공간을 만들어 보세요.</p>
    <form onSubmit={submit}>
      <label className="type-caption" htmlFor="project-name">프로젝트 이름 <span aria-hidden="true">*</span></label>
      <Input ref={nameInput} id="project-name" value={name} onChange={event => setName(event.target.value)}
        placeholder="예: 체험단 서비스" autoFocus required disabled={create.isPending} />
      <label className="type-caption" htmlFor="project-description">설명 <span className="optional-label type-label">선택</span></label>
      <Textarea id="project-description" value={description} onChange={event => setDescription(event.target.value)}
        placeholder="어떤 서비스의 정책을 관리하나요?" rows={3} disabled={create.isPending} />
      {create.isError && <p className="project-error type-caption" role="alert">{create.error.message}</p>}
      <div className="project-dialog-actions">
        <Button type="button" variant="outline" disabled={create.isPending} onClick={close}>취소</Button>
        <Button type="submit" disabled={create.isPending || !name.trim()}>
          {create.isPending ? <LoaderCircle className="animate-spin" /> : <Plus />}
          {create.isPending ? "생성 중…" : "프로젝트 생성"}
        </Button>
      </div>
    </form>
  </dialog>;
}
