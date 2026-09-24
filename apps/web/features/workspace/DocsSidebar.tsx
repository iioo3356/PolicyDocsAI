import type { Policy } from "@/domain/Policy";
import { WorkspaceIcon } from "./WorkspaceIcon";

export function DocsSidebar({ policies, selectedId, onSelect, searching }: {
  policies: Policy[];
  selectedId?: string;
  onSelect: (id: string) => void;
  searching: boolean;
}) {
  const groups = policies.reduce<Record<string, Policy[]>>((result, policy) => {
    (result[policy.category] ??= []).push(policy);
    return result;
  }, {});
  return (
    <aside className="docs-sidebar" aria-label="문서 주제">
      <div className="sidebar-heading"><span>주제</span><span>{policies.length}</span></div>
      <nav aria-label="정책 문서 목록">
        {Object.entries(groups).map(([category, items]) => (
          <section className="topic-group" key={category}>
            <h2>{category}</h2>
            {items.map(policy => (
              <button key={policy.id} type="button" onClick={() => onSelect(policy.id)}
                className={`topic-link ${selectedId === policy.id ? "is-active" : ""}`}
                aria-current={selectedId === policy.id ? "page" : undefined}>
                <WorkspaceIcon name="file" /><span>{policy.title}</span>
              </button>
            ))}
          </section>
        ))}
        {policies.length === 0 && <p className="sidebar-empty">
          {searching ? "일치하는 주제가 없습니다." : "승인된 문서가 여기에 표시됩니다."}
        </p>}
      </nav>
    </aside>
  );
}
