"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, FolderOpen, Plus, LoaderCircle } from "lucide-react";
import { api, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PolicyDocsLogo } from "@/components/PolicyDocsLogo";
import { CreateProjectDialog } from "@/features/projects/CreateProjectDialog";

export default function Projects() {
  const [creating, setCreating] = useState(false);
  const projects = useQuery({ queryKey: ["projects"], queryFn: () => api<Project[]>("/projects") });
  return <main className="projects-home">
    <div className="projects-home-content">
      <header className="projects-brand">
        <h1><PolicyDocsLogo /></h1>
        <p className="type-caption">근거에서 시작하는 명확한 정책 문서</p>
      </header>
      <section className="projects-section" aria-labelledby="projects-heading">
        <div className="projects-section-heading"><h2 className="type-subheading" id="projects-heading">프로젝트</h2>
          <span className="type-label">{projects.data?.length ?? "—"} WORKSPACES</span>
        </div>
        {projects.isPending && <div className="projects-state" role="status"><LoaderCircle size={20} className="animate-spin" />프로젝트를 불러오고 있어요.</div>}
        {projects.isError && <div className="projects-state project-error" role="alert">
          <p className="type-caption">프로젝트를 불러오지 못했습니다.</p><p className="type-caption">{projects.error.message}</p>
          <Button variant="outline" onClick={() => projects.refetch()}>다시 시도</Button>
        </div>}
        <div className="projects-list">
          {projects.data?.map(project => <Link href={`/projects/${project.id}`} className="project-link" key={project.id}>
            <span className="project-icon"><FolderOpen size={21} /></span>
            <span className="project-details"><strong className="type-subheading">{project.name}</strong><span className="type-caption">{project.description || "정책과 근거를 정리하는 공간"}</span></span>
            <ArrowUpRight size={19} className="project-arrow" />
          </Link>)}
        </div>
        {projects.data?.length === 0 && <div className="projects-state">
          <span className="project-icon"><FolderOpen size={24} /></span>
          <h3 className="type-subheading">첫 번째 정책 공간을 만들어 보세요</h3><p className="type-caption">프로젝트별로 소스와 정책 문서를 관리할 수 있어요.</p>
        </div>}
      </section>
      <div className="projects-create">
        <Button size="lg" onClick={() => setCreating(true)}><Plus size={17} />프로젝트 생성</Button>
        <p className="type-caption">서비스마다 독립적인 워크스페이스를 만들어 보세요.</p>
      </div>
      <footer className="projects-footer type-label">POLICY DOCS · KNOWLEDGE, WITH EVIDENCE</footer>
    </div>
    {creating && <CreateProjectDialog onClose={() => setCreating(false)} />}
  </main>;
}
