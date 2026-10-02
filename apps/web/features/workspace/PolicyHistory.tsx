import type { PolicyRevision } from "@/domain/PolicyRevision";

export function PolicyHistory({ revisions }: { revisions: PolicyRevision[] }) {
  return <section className="evidence-section" aria-labelledby="history-heading">
    <div className="section-eyebrow type-label">HISTORY</div><h2 className="type-heading" id="history-heading">수정 이력</h2>
    {!revisions.length && <p className="evidence-description type-caption">아직 수정 이력이 없습니다.</p>}
    {revisions.map(revision => <details key={revision.id} className="evidence-item">
      <summary className="type-caption">{revision.after._deprecation ? `정책 폐기 · ${revision.after._deprecation.name}`
        : revision.after._source ? `소스 업데이트 · ${revision.after._source.name}` : "이전 정책 수정"} · {new Date(`${revision.created_at}Z`).toLocaleString("ko-KR")}</summary>
      <p className="muted type-caption">{revision.instruction}</p>
      <div className="chat-diff">
        <div><h3 className="type-caption">변경 전</h3><strong className="type-subheading">{revision.before.title}</strong><p className="type-body">{revision.before.category} · {revision.before.summary}</p><ul className="type-body">{revision.before.rules.map((rule, i) => <li key={i}>{rule}</li>)}</ul></div>
        <div><h3 className="type-caption">변경 후</h3><strong className="type-subheading">{revision.after.title}</strong><p className="type-body">{revision.after.category} · {revision.after.summary}</p><ul className="type-body">{revision.after.rules.map((rule, i) => <li key={i}>{rule}</li>)}</ul></div>
      </div>
    </details>)}
  </section>;
}
