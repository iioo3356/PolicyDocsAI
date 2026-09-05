"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api, Project } from "@/lib/api";

export default function Projects() {
 const qc=useQueryClient(); const [name,setName]=useState(""); const [description,setDescription]=useState("");
 const projects=useQuery({queryKey:["projects"],queryFn:()=>api<Project[]>("/projects")});
 const create=useMutation({mutationFn:()=>api<Project>("/projects",{method:"POST",body:JSON.stringify({name,description})}),onSuccess:()=>{setName("");setDescription("");qc.invalidateQueries({queryKey:["projects"]})}});
 function submit(e:FormEvent){e.preventDefault();if(name.trim())create.mutate()}
 return <main className="container">
  <div className="row between"><div><h1>Projects</h1><p className="muted">서비스별 정책과 근거를 독립적으로 관리합니다.</p></div></div>
  <div className="split">
   <section className="card sticky"><h2>새 Project</h2><form onSubmit={submit}><label>이름</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="체험단 서비스" required/><label>설명</label><textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="선택 사항"/><button className="primary" disabled={create.isPending}>{create.isPending?"생성 중":"Project 생성"}</button>{create.error&&<p className="small" style={{color:"#b42318"}}>{create.error.message}</p>}</form></section>
   <section><h2>Project 목록</h2><div className="list">{projects.data?.map(p=><Link href={`/projects/${p.id}`} className="item" key={p.id}><div className="row between"><strong>{p.name}</strong><span>→</span></div><p className="muted small">{p.description||"설명 없음"}</p></Link>)}{projects.data?.length===0&&<div className="card empty">첫 Project를 생성하세요.</div>}</div></section>
  </div>
 </main>
}

