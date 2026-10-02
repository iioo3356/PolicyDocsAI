"use client";

import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { WorkspaceIcon } from "./WorkspaceIcon";

export function WorkspacePanel({ title, onClose, children }: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog ref={ref} className="workspace-dialog" aria-labelledby="workspace-panel-title"
      onCancel={event => { event.preventDefault(); onClose(); }}
      onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="panel-surface">
        <header className="panel-header">
          <div><span className="section-eyebrow type-label">WORKSPACE</span><h2 className="type-heading" id="workspace-panel-title">{title}</h2></div>
          <Button variant="ghost" size="icon" type="button" aria-label="닫고 문서로 돌아가기" onClick={onClose} autoFocus>
            <WorkspaceIcon name="close" />
          </Button>
        </header>
        <div className="panel-content">{children}</div>
      </div>
    </dialog>
  );
}
