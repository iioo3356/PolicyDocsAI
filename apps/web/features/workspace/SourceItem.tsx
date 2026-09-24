"use client";
import { api, Source } from "@/lib/api";
import type { SourceAnalysis } from "@/domain/SourceAnalysis";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";


export function SourceItem({ source, roles, onChanged, onUpdate }: {
  source: Source; roles: string[]; onChanged: () => void; onUpdate: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [role, setRole] = useState(source.role);
  const busy = source.status === "PENDING" || source.status === "PROCESSING";
  const analysis = useQuery({
    queryKey: ["source-analysis", source.id],
    queryFn: () => api<SourceAnalysis>(`/sources/${source.id}/analysis`),
    refetchInterval: busy ? 1000 : false,
  });
  const save = useMutation({
    mutationFn: () => api<Source>(`/sources/${source.id}/role`, {
      method: "PATCH", body: JSON.stringify({ role }),
    }),
    onSuccess: () => { setEditing(false); onChanged(); },
  });
  const remove = useMutation({
    mutationFn: () => api<void>(`/sources/${source.id}`, { method: "DELETE" }),
    onSuccess: onChanged,
  });
  function confirmDelete() {
    if (window.confirm(`'${source.name}' Source와 분석 결과를 삭제할까요?`)) remove.mutate();
  }
  const result = analysis.data;
  return <div className="item">
    <div className="row between"><strong>{source.name}</strong><span className={`badge ${source.status}`}>{source.status}</span></div>
    {editing ? <div className="row source-actions">
      <input list={`roles-${source.id}`} value={role} onChange={event => setRole(event.target.value)} autoFocus />
      <datalist id={`roles-${source.id}`}>{roles.map(item => <option value={item} key={item} />)}</datalist>
      <button className="primary" disabled={!role.trim() || save.isPending} onClick={() => save.mutate()}>저장</button>
      <button onClick={() => { setRole(source.role); setEditing(false); }}>취소</button>
    </div> : <div className="row between source-actions">
      <span className="muted small">역할: {source.role} · {source.kind} · 발견 {result?.candidates.length ?? source.discovered_policy_count}개</span>
      <div className="row"><button className="small" disabled={source.status !== "COMPLETED"} onClick={onUpdate}>업데이트</button>
        <button className="small" onClick={() => setEditing(true)}>역할 변경</button>
        <button className="danger small" disabled={busy || remove.isPending} title={busy ? "분석이 끝난 뒤 삭제할 수 있습니다." : undefined} onClick={confirmDelete}>
          {remove.isPending ? "삭제 중" : busy ? "분석 중" : "삭제"}
        </button></div>
    </div>}
    {busy && <div className="analysis-live" aria-live="polite">
      <div className="row between"><strong>정책 분석 중</strong><span>{result?.progress ?? 0}%</span></div>
      <progress max="100" value={result?.progress ?? 0} />
      {result?.current_file && <p className="muted small" title={result.current_file}>확인 중: {result.current_file}</p>}
      {result?.current_policy_title && <p className="small">방금 찾은 정책: <strong>{result.current_policy_title}</strong></p>}
      {!!result?.total_files && <p className="muted small">파일 {result.processed_files}/{result.total_files}</p>}
    </div>}
    {!!result?.candidates.length && <div className="analysis-policies">
      <strong>{busy ? "지금까지 찾은 정책 후보" : "추가된 정책 후보"}</strong>
      <ol>{result.candidates.map(candidate => <li key={candidate.id}>
        <span>{candidate.title}</span><small>{candidate.category} · {Math.round(candidate.confidence * 100)}%</small>
      </li>)}</ol>
    </div>}
    {busy && !result?.candidates.length && <p className="muted small">코드에서 정책 후보를 찾고 있습니다…</p>}
    {analysis.error && <p role="alert" className="small">분석 진행 상황을 불러오지 못했습니다. {analysis.error.message}</p>}
    {save.error && <p role="alert" className="small">{save.error.message}</p>}
    {remove.error && <p role="alert" className="small">{remove.error.message}</p>}
    {source.error_message && <p role="alert">{source.error_message}</p>}
  </div>;
}
