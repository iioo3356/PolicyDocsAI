"use client";
import { api, Source } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { SourceItem } from "./SourceItem";

export function Sources({ id }: { id: string }) {
  const qc = useQueryClient();
  const params = useSearchParams();
  const [replacement, setReplacement] = useState(params.get("replace_source_id") || "");
  const [file, setFile] = useState<File>();
  const [role, setRole] = useState("document");
  const input = useRef<HTMLInputElement>(null);
  const q = useQuery({ queryKey: ["sources", id], queryFn: () => api<Source[]>(`/projects/${id}/sources`), refetchInterval: 3000 });
  const previous = q.data?.find(source => source.id === replacement);
  const upload = useMutation({
    mutationFn: () => {
      const data = new FormData();
      data.append("file", file!);
      data.append("role", previous?.role || role);
      if (replacement) data.append("replaces_source_id", replacement);
      return api(`/projects/${id}/sources`, { method: "POST", body: data });
    },
    onSuccess: () => {
      setFile(undefined);
      if (input.current) input.current.value = "";
      refresh();
    },
  });
  const knownRoles = Array.from(new Set(["document", "frontend", "app", "backend", ...(q.data ?? []).map(s => s.role)]));
  function refresh() {
    for (const key of ["sources", "dashboard", "candidates"]) qc.invalidateQueries({ queryKey: [key, id] });
  }
  return <div className="split">
    <section className="card sticky">
      <h2>소스 추가·업데이트</h2>
      <label htmlFor="replace-source">업데이트할 기존 소스</label>
      <select id="replace-source" value={replacement} disabled={upload.isPending} onChange={event => { setReplacement(event.target.value); upload.reset(); }}>
        <option value="">새 소스 추가</option>
        {q.data?.filter(source => source.status === "COMPLETED").map(source =>
          <option key={source.id} value={source.id}>{source.name} · {source.role} · {source.id.slice(0, 8)}</option>)}
      </select>
      {replacement && <p className="muted small">같은 형식의 최신 파일을 올려 주세요. 기존 정책은 유지되며, 정책 관리에서 변경안을 승인하면 수정 이력이 저장됩니다.</p>}
      <label htmlFor="source-role">소스 역할</label>
      <input id="source-role" list="source-role-options" value={previous?.role || role} disabled={!!replacement || upload.isPending} onChange={e => setRole(e.target.value)} />
      <datalist id="source-role-options">{knownRoles.map(item => <option value={item} key={item} />)}</datalist>
      <label htmlFor="source-file">ZIP / Markdown / CSV / XLSX</label>
      <input id="source-file" ref={input} type="file" disabled={upload.isPending} accept=".zip,.md,.markdown,.csv,.xlsx" onChange={e => { setFile(e.target.files?.[0]); upload.reset(); }} />
      <p className="muted small">코드는 ZIP으로 업로드하세요. 최대 25MB.</p>
      <button className="primary" disabled={!file || !role.trim() || upload.isPending || (!!replacement && !previous)} onClick={() => upload.mutate()}>
        {upload.isPending ? "업로드 중…" : replacement ? "업데이트 및 재분석" : "업로드 및 분석"}
      </button>
      {upload.isSuccess && <p role="status">소스를 등록했습니다. 분석이 끝나면 <Link href={`/projects/${id}/reviews`}>정책 관리에서 변경안을 검토</Link>해 주세요.</p>}
      {upload.error && <p role="alert">{upload.error.message}</p>}
      {q.error && <p role="alert">{q.error.message}</p>}
    </section>
    <section><h2>등록된 소스</h2><div className="list">
      {q.data?.map(source => <SourceItem key={source.id} source={source} roles={knownRoles} onChanged={refresh}
        onUpdate={() => { setReplacement(source.id); upload.reset(); input.current?.focus(); }} />)}
      {q.data?.length === 0 && <div className="card empty">소스를 업로드하면 정책 후보를 찾습니다.</div>}
    </div></section>
  </div>;
}
