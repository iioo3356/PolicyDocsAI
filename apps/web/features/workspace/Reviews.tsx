"use client";
import { api, Candidate } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function Reviews({ id }: { id: string }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["candidates", id], queryFn: () => api<Candidate[]>(`/projects/${id}/policy-candidates`), refetchInterval: 3000 });
  const [selected, setSelected] = useState<string>();
  useEffect(() => { if (!q.data?.some(c => c.id === selected)) setSelected(q.data?.[0]?.id); }, [q.data, selected]);
  const detail = useQuery({ queryKey: ["candidate", selected], queryFn: () => api<Candidate>(`/policy-candidates/${selected}`), enabled: !!selected });
  const [form, setForm] = useState({ title: "", summary: "", category: "", rules: "" });
  const [target, setTarget] = useState("");
  useEffect(() => {
    if (detail.data) {
      setForm({ title: detail.data.title, summary: detail.data.summary, category: detail.data.category, rules: detail.data.rules.join("\n") });
      setTarget(detail.data.proposed_policy_id || "");
    }
  }, [detail.data]);
  const current = detail.data?.related_policies?.find(policy => policy.id === target);
  const review = useMutation({
    mutationFn: (action: "approve" | "reject") => api(`/policy-candidates/${selected}/${action}`, {
      method: "POST", ...(action === "approve" ? { body: JSON.stringify({ ...form, rules: form.rules.split("\n").map(r => r.trim()).filter(Boolean), target_policy_id: target || null }) } : {}),
    }),
    onSuccess: () => {
      setSelected(undefined);
      for (const key of ["candidates", "dashboard", "policies"]) qc.invalidateQueries({ queryKey: [key, id] });
      qc.invalidateQueries({ queryKey: ["policy-history"] });
      qc.invalidateQueries({ queryKey: ["candidate"] });
    },
  });
  return <>
    {(q.error || detail.error || review.error) && <p role="alert">{(q.error || detail.error || review.error)?.message}</p>}
    <div className="three">
      <section className="list">{q.data?.map(candidate => <button key={candidate.id} disabled={review.isPending} onClick={() => setSelected(candidate.id)} style={{ textAlign: "left", borderColor: selected === candidate.id ? "#2463eb" : undefined }}>
        <strong>{candidate.title}</strong><div className="muted small">{candidate.category} · {Math.round(candidate.confidence * 100)}%{candidate.proposed_policy_id ? " · 업데이트 후보" : ""}</div>
      </button>)}{q.data?.length === 0 && <div className="card empty">검토할 후보가 없습니다.</div>}</section>
      {detail.data && selected === detail.data.id ? <>
        <section className="card">
          <h2>{target ? "정책 변경 검토" : "새 정책 검토"}</h2>
          {detail.data.previous_source_id && <>
            <label htmlFor="review-target">연결할 기존 정책</label>
            <select id="review-target" value={target} disabled={review.isPending} onChange={e => setTarget(e.target.value)}>
              {!detail.data.proposed_policy_id && <option value="">새 정책으로 등록</option>}
              {detail.data.related_policies?.map(policy => <option key={policy.id} value={policy.id}>{policy.title}</option>)}
            </select>
            <p className="muted small">관련 정책과 변경 내용을 확인해 주세요. 제목·요약·규칙 전체가 아래 내용으로 교체됩니다.</p>
          </>}
          {current && <details open className="chat-change"><summary>변경 전</summary><h3>{current.title}</h3><p>{current.category} · {current.summary}</p><ul>{current.rules.map(rule => <li key={rule.id}>{rule.content}</li>)}</ul></details>}
          <h3>{target ? "변경 후" : "승인할 내용"}</h3>
          <label htmlFor="review-title">제목</label><input id="review-title" value={form.title} disabled={review.isPending} onChange={e => setForm({ ...form, title: e.target.value })} />
          <label htmlFor="review-summary">요약</label><textarea id="review-summary" value={form.summary} disabled={review.isPending} onChange={e => setForm({ ...form, summary: e.target.value })} />
          <label htmlFor="review-category">주제</label><input id="review-category" value={form.category} disabled={review.isPending} onChange={e => setForm({ ...form, category: e.target.value })} />
          <label htmlFor="review-rules">규칙 (한 줄에 하나)</label><textarea id="review-rules" value={form.rules} disabled={review.isPending} onChange={e => setForm({ ...form, rules: e.target.value })} />
          <p className="muted small">{target ? "변경 승인을 누르면 정책에 반영되고 이전 내용과 소스가 이력에 남습니다." : "승인을 누르면 새 정책이 등록됩니다."}</p>
          <div className="row"><button className="primary" disabled={review.isPending || !form.title.trim() || !form.summary.trim() || (!!target && !current)} onClick={() => review.mutate("approve")}>{target ? "변경 승인" : "새 정책 승인"}</button>
            <button className="danger" disabled={review.isPending} onClick={() => review.mutate("reject")}>반려</button></div>
        </section>
        <section className="card"><h2>새 소스 근거</h2><p className="small"><strong>{detail.data.source_name}</strong><br />{detail.data.source_path}:{detail.data.start_line}-{detail.data.end_line}</p><pre className="source">{detail.data.excerpt}</pre></section>
      </> : <section className="card empty">{detail.isPending && selected ? "후보를 불러오는 중…" : "후보를 선택하세요."}</section>}
    </div>
  </>;
}
