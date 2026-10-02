"use client";

import { api, Policy } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { DocsSidebar } from "./DocsSidebar";
import { PolicyArticle } from "./PolicyArticle";
import { PolicyDocsLogo } from "@/components/PolicyDocsLogo";
import { WorkspaceIcon } from "./WorkspaceIcon";

export function Docs({ id, projectName }: { id: string; projectName: string }) {
  const workspace = useRef<HTMLDivElement>(null);
  const header = useRef<HTMLElement>(null);
  useEffect(() => {
    const node = header.current;
    if (!node) return;
    const updateHeight = () => workspace.current?.style.setProperty(
      "--docs-header-height", `${node.getBoundingClientRect().height}px`,
    );
    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string>();
  const query = useQuery({
    queryKey: ["policies", id],
    queryFn: () => api<Policy[]>(`/projects/${id}/policies`),
  });
  const terms = search.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const policies = (query.data ?? []).filter(policy => {
    const text = [policy.title, policy.category, policy.summary, ...policy.rules.map(rule => rule.content)]
      .join(" ").toLocaleLowerCase();
    return terms.every(term => text.includes(term));
  });
  const policy = policies.find(item => item.id === selected) ?? policies[0];

  return (
    <div ref={workspace} className="docs-workspace">
      <header ref={header} className="docs-topbar">
        <Link href="/" className="docs-brand" aria-label="Policy Docs 프로젝트 목록">
          <PolicyDocsLogo compact />
        </Link>
        <div className="docs-search" role="search">
          <WorkspaceIcon name="search" />
          <input aria-label="문서 검색" placeholder="어떤 정책을 찾고 있나요?"
            value={search} onChange={event => setSearch(event.target.value)} />
          {search && <button type="button" aria-label="검색어 지우기" onClick={() => setSearch("")}>
            <WorkspaceIcon name="close" />
          </button>}
        </div>
        <Link className="workspace-project type-caption" href="/" title="프로젝트 변경">{projectName}</Link>
      </header>
      <div className="docs-grid">
        <DocsSidebar policies={policies} selectedId={policy?.id} onSelect={setSelected} searching={!!terms.length} />
        <main className="docs-content" aria-label="정책 설명">
          {query.isPending ? <div className="docs-state" role="status">문서를 불러오고 있습니다…</div>
            : query.isError ? <div className="docs-state" role="alert">
              <h1 className="type-heading">문서를 불러오지 못했습니다</h1><p className="type-body">{query.error.message}</p>
              <button onClick={() => query.refetch()}>다시 시도</button>
            </div> : policy ? <PolicyArticle policy={policy} />
              : <div className="docs-state">
                <span className="empty-doc-icon"><WorkspaceIcon name={terms.length ? "search" : "book"} /></span>
                <div className="section-eyebrow type-label">YOUR KNOWLEDGE, ORGANIZED</div>
                <h1 className="type-heading">{terms.length ? "검색 결과가 없습니다" : "정책이 모이면, 기준이 선명해집니다"}</h1>
                <p className="type-body">{terms.length ? "다른 검색어로 제목, 주제 또는 규칙을 찾아보세요."
                  : "소스를 추가하고 정책 후보를 선택해 보세요.\n승인된 문서를 이곳에서 편하게 읽을 수 있습니다."}</p>
                {terms.length ? <button onClick={() => setSearch("")}>전체 문서 보기</button>
                  : <Link className="empty-doc-action type-caption" href={`/projects/${id}/sources`}>첫 소스 추가하기 <span>↗</span></Link>}
              </div>}
        </main>
        <div className="docs-gutter" aria-hidden="true" />
      </div>
    </div>
  );
}
