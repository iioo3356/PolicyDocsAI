"use client";

import { api, Project } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Chat } from "@/features/workspace/Chat";
import { Dashboard } from "@/features/workspace/Dashboard";
import { Docs } from "@/features/workspace/Docs";
import { Reviews } from "@/features/workspace/Reviews";
import { Sources } from "@/features/workspace/Sources";
import { WorkspaceIcon } from "@/features/workspace/WorkspaceIcon";
import { WorkspacePanel } from "@/features/workspace/WorkspacePanel";

const actions = [
  { section: "sources", label: "소스 추가", icon: "plus", title: "소스 추가 및 관리" },
  { section: "reviews", label: "정책 관리", icon: "select", title: "정책 후보 검토 및 승인" },
  { section: "chat", label: "채팅", icon: "chat", title: "정책에 대해 질문하기" },
];

export function Workspace({ projectId, section }: { projectId: string; section: string }) {
  const router = useRouter();
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api<Project>(`/projects/${projectId}`),
  });
  const action = actions.find(item => item.section === section);
  const title = action?.title ?? (section === "dashboard" ? "프로젝트 현황" : undefined);
  const close = () => router.push(`/projects/${projectId}`, { scroll: false });

  if (project.isError) return <main className="container docs-state" role="alert">
    <h1>프로젝트를 불러오지 못했습니다</h1><p>{project.error.message}</p>
    <Link href="/">프로젝트 목록으로 돌아가기</Link>
  </main>;

  return (
    <>
      <Docs key={projectId} id={projectId} projectName={project.data?.name ?? "불러오는 중…"} />
      <nav className="floating-tools" aria-label="문서 도구">
        {actions.map(item => <Link key={item.section} href={`/projects/${projectId}/${item.section}`}
          scroll={false} aria-label={item.title} aria-haspopup="dialog">
          <WorkspaceIcon name={item.icon} /><span>{item.label}</span>
        </Link>)}
      </nav>
      {title && <WorkspacePanel key={section} title={title} onClose={close}>
        {section === "sources" && <Sources id={projectId} />}
        {section === "reviews" && <Reviews id={projectId} />}
        {section === "chat" && <Chat id={projectId} />}
        {section === "dashboard" && <Dashboard id={projectId} />}
      </WorkspacePanel>}
    </>
  );
}
