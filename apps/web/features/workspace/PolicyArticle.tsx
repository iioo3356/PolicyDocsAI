"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PolicyRevision } from "@/domain/PolicyRevision";
import { PolicyHistory } from "./PolicyHistory";
import type { Policy } from "@/domain/Policy";
import { WorkspaceIcon } from "./WorkspaceIcon";

export function PolicyArticle({ policy }: { policy: Policy }) {
  const history = useQuery({ queryKey: ["policy-history", policy.id], queryFn: () => api<PolicyRevision[]>(`/policies/${policy.id}/revisions`) });
  const currentChunk = history.data?.[0]?.after._source?.source_chunk_id;
  return (
    <article className="policy-article" key={policy.id}>
      <div className="doc-breadcrumb">Docs <span>/</span> {policy.category}</div>
      <div className="article-status"><span className="status-dot" />승인된 정책
        {policy.has_conflict && <span className="conflict-note">확인이 필요한 충돌이 있습니다</span>}
      </div>
      <h1>{policy.title}</h1>
      <p className="article-summary">{policy.summary}</p>
      <div className="article-divider" />
      <section aria-labelledby="rules-heading">
        <div className="section-eyebrow">POLICY DETAILS</div>
        <h2 id="rules-heading">상세 규칙</h2>
        {policy.rules.length ? <ol className="policy-rules">
          {policy.rules.map((rule, index) => <li key={rule.id}>
            <span className="rule-number">{String(index + 1).padStart(2, "0")}</span>
            <p>{rule.content}</p>
          </li>)}
        </ol> : <p className="muted">등록된 상세 규칙이 없습니다.</p>}
      </section>
      <section className="evidence-section" aria-labelledby="evidence-heading">
        <div className="section-eyebrow">REFERENCES</div>
        <h2 id="evidence-heading">이 문서의 근거</h2>
        <p className="evidence-description">정책이 어디에서 왔는지 원본을 확인하세요.</p>
        {policy.evidence.map(evidence => (
          <details className="evidence-item" key={evidence.id}>
            <summary><WorkspaceIcon name="file" /><span>
              <strong>{evidence.source_name}{currentChunk && evidence.source_chunk_id !== currentChunk ? " · 이전 버전 근거" : ""}</strong>
              <small>{evidence.source_path} · {evidence.start_line}–{evidence.end_line}줄</small>
            </span><span className="evidence-role">{evidence.source_type}</span></summary>
            <pre className="source">{evidence.excerpt}</pre>
          </details>
        ))}
        {!policy.evidence.length && <p className="muted">연결된 근거가 없습니다.</p>}
      </section>
      {history.error && <p role="alert">수정 이력을 불러오지 못했습니다. {history.error.message}</p>}
      {history.isPending && <p role="status">수정 이력을 불러오는 중…</p>}
      {history.data && <PolicyHistory revisions={history.data} />}
      <footer className="article-footer">POLICY DOCS <span>근거에서 시작하는 명확한 기준</span></footer>
    </article>
  );
}
