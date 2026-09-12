"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { api, Candidate, Policy, Project, Source } from "@/lib/api";

const tabs=[['dashboard','Dashboard'],['sources','Sources'],['reviews','Policy Review'],['policies','Policy Docs'],['chat','AI Chat']];

export function Workspace({projectId,section}:{projectId:string;section:string}){
 const project=useQuery({queryKey:["project",projectId],queryFn:()=>api<Project>(`/projects/${projectId}`)});
 return <main className="container"><div className="row between"><div><Link className="muted small" href="/">← Projects</Link><h1>{project.data?.name??"Loading…"}</h1></div></div><nav className="tabs">{tabs.map(([key,label])=><Link key={key} className={`tab ${section===key?'active':''}`} href={`/projects/${projectId}/${key}`}>{label}</Link>)}</nav>
 {section==='dashboard'?<Dashboard id={projectId}/>:section==='sources'?<Sources id={projectId}/>:section==='reviews'?<Reviews id={projectId}/>:section==='policies'?<Docs id={projectId}/>:<Chat id={projectId}/>}</main>
}

function Dashboard({id}:{id:string}){
 const q=useQuery({queryKey:["dashboard",id],queryFn:()=>api<any>(`/projects/${id}/dashboard`),refetchInterval:3000});
 const items=[['등록 Source',q.data?.source_count],['전체 Policy',q.data?.policy_count],['Review 필요',q.data?.review_count],['Conflict',q.data?.conflict_count]];
 return <div className="grid cards">{items.map(([label,value])=><div className="card" key={label as string}><div className="muted small">{label}</div><div className="stat">{value??'—'}</div></div>)}</div>
}

function Sources({id}:{id:string}){
 const qc=useQueryClient(); const [file,setFile]=useState<File>(); const [role,setRole]=useState('document');
 const q=useQuery({queryKey:["sources",id],queryFn:()=>api<Source[]>(`/projects/${id}/sources`),refetchInterval:3000});
 const upload=useMutation({mutationFn:()=>{const data=new FormData();data.append('file',file!);data.append('role',role);return api(`/projects/${id}/sources`,{method:'POST',body:data})},onSuccess:()=>{setFile(undefined);qc.invalidateQueries({queryKey:['sources',id]})}});
 const knownRoles=Array.from(new Set(['document','frontend','app','backend',...(q.data??[]).map(s=>s.role)]));
 function refresh(){qc.invalidateQueries({queryKey:['sources',id]});qc.invalidateQueries({queryKey:['dashboard',id]});qc.invalidateQueries({queryKey:['candidates',id]})}
 return <div className="split"><section className="card sticky"><h2>Source 업로드</h2><label>Source 역할</label><input list="source-role-options" value={role} onChange={e=>setRole(e.target.value)} placeholder="예: admin-web, payment-backend"/><datalist id="source-role-options">{knownRoles.map(item=><option value={item} key={item}/>)}</datalist><p className="muted small">목록에서 선택하거나 새 역할을 직접 입력할 수 있습니다.</p><label>ZIP / Markdown / CSV / XLSX</label><input type="file" accept=".zip,.md,.markdown,.csv,.xlsx" onChange={e=>setFile(e.target.files?.[0])}/><p className="muted small">코드는 ZIP으로 업로드하세요. 최대 25MB.</p><button className="primary" disabled={!file||!role.trim()||upload.isPending} onClick={()=>upload.mutate()}>{upload.isPending?'업로드 중':'업로드 및 분석'}</button>{upload.error&&<p style={{color:'#b42318'}} className="small">{upload.error.message}</p>}</section><section><h2>등록된 Source</h2><div className="list">{q.data?.map(s=><SourceItem key={s.id} source={s} roles={knownRoles} onChanged={refresh}/>)}{q.data?.length===0&&<div className="card empty">Source를 업로드하면 정책 후보를 찾습니다.</div>}</div></section></div>
}

function SourceItem({source,roles,onChanged}:{source:Source;roles:string[];onChanged:()=>void}){
 const [editing,setEditing]=useState(false); const [role,setRole]=useState(source.role);
 const save=useMutation({mutationFn:()=>api<Source>(`/sources/${source.id}/role`,{method:'PATCH',body:JSON.stringify({role})}),onSuccess:()=>{setEditing(false);onChanged()}});
 const remove=useMutation({mutationFn:()=>api<void>(`/sources/${source.id}`,{method:'DELETE'}),onSuccess:onChanged});
 function confirmDelete(){if(window.confirm(`'${source.name}' Source와 분석 결과를 삭제할까요?`))remove.mutate()}
 const busy=source.status==='PENDING'||source.status==='PROCESSING';
 return <div className="item"><div className="row between"><strong>{source.name}</strong><span className={`badge ${source.status}`}>{source.status}</span></div>{editing?<div className="row" style={{marginTop:10}}><input list={`roles-${source.id}`} value={role} onChange={e=>setRole(e.target.value)} autoFocus/><datalist id={`roles-${source.id}`}>{roles.map(item=><option value={item} key={item}/>)}</datalist><button className="primary" disabled={!role.trim()||save.isPending} onClick={()=>save.mutate()}>저장</button><button onClick={()=>{setRole(source.role);setEditing(false)}}>취소</button></div>:<div className="row between" style={{marginTop:8}}><span className="muted small">역할: {source.role} · {source.kind} · 발견 {source.discovered_policy_count}개</span><div className="row"><button className="small" onClick={()=>setEditing(true)}>역할 변경</button><button className="danger small" disabled={busy||remove.isPending} title={busy?'분석이 끝난 뒤 삭제할 수 있습니다.':undefined} onClick={confirmDelete}>{remove.isPending?'삭제 중':busy?'분석 중':'삭제'}</button></div></div>}{busy&&<p className="muted small">분석 중에는 삭제할 수 없습니다. API 재시작으로 중단된 작업은 자동으로 실패 처리됩니다.</p>}{save.error&&<p style={{color:'#b42318'}} className="small">{save.error.message}</p>}{remove.error&&<p style={{color:'#b42318'}} className="small">{remove.error.message}</p>}{source.error_message&&<p style={{color:'#b42318'}}>{source.error_message}</p>}</div>
}

function Reviews({id}:{id:string}){
 const qc=useQueryClient(); const q=useQuery({queryKey:['candidates',id],queryFn:()=>api<Candidate[]>(`/projects/${id}/policy-candidates`)}); const [selected,setSelected]=useState<string>();
 useEffect(()=>{if(!selected&&q.data?.[0])setSelected(q.data[0].id)},[q.data,selected]);
 const detail=useQuery({queryKey:['candidate',selected],queryFn:()=>api<Candidate>(`/policy-candidates/${selected}`),enabled:!!selected});
 const [form,setForm]=useState({title:'',summary:'',category:'',rules:''});
 useEffect(()=>{if(detail.data)setForm({title:detail.data.title,summary:detail.data.summary,category:detail.data.category,rules:detail.data.rules.join('\n')})},[detail.data]);
 const review=useMutation({mutationFn:(action:'approve'|'reject')=>action==='reject'?api(`/policy-candidates/${selected}/reject`,{method:'POST'}):api(`/policy-candidates/${selected}/approve`,{method:'POST',body:JSON.stringify({...form,rules:form.rules.split('\n').filter(Boolean)})}),onSuccess:()=>{setSelected(undefined);qc.invalidateQueries({queryKey:['candidates',id]});qc.invalidateQueries({queryKey:['dashboard',id]})}});
 return <div className="three"><section className="list">{q.data?.map(c=><button key={c.id} onClick={()=>setSelected(c.id)} style={{textAlign:'left',borderColor:selected===c.id?'#2463eb':undefined}}><strong>{c.title}</strong><div className="muted small">{c.category} · {Math.round(c.confidence*100)}%</div></button>)}{q.data?.length===0&&<div className="card empty">검토할 후보가 없습니다.</div>}</section>{detail.data?<><section className="card"><h2>정책 편집</h2><label>제목</label><input value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/><label>요약</label><textarea value={form.summary} onChange={e=>setForm({...form,summary:e.target.value})}/><label>Category</label><input value={form.category} onChange={e=>setForm({...form,category:e.target.value})}/><label>Rules (한 줄에 하나)</label><textarea value={form.rules} onChange={e=>setForm({...form,rules:e.target.value})}/><div className="row"><button className="primary" onClick={()=>review.mutate('approve')}>Approve</button><button className="danger" onClick={()=>review.mutate('reject')}>Reject</button></div></section><section className="card"><h2>Source 근거</h2><p className="small"><strong>{detail.data.source_name}</strong><br/>{detail.data.source_path}:{detail.data.start_line}-{detail.data.end_line}</p><pre className="source">{detail.data.excerpt}</pre></section></>:<section className="card empty">후보를 선택하세요.</section>}</div>
}

function Docs({id}:{id:string}){
 const q=useQuery({queryKey:['policies',id],queryFn:()=>api<Policy[]>(`/projects/${id}/policies?status=APPROVED`)}); const [selected,setSelected]=useState<string>(); useEffect(()=>{if(!selected&&q.data?.[0])setSelected(q.data[0].id)},[q.data,selected]); const policy=q.data?.find(p=>p.id===selected);
 const grouped=(q.data??[]).reduce<Record<string,Policy[]>>((a,p)=>((a[p.category]??=[]).push(p),a),{});
 return <div className="split"><aside className="card sticky">{Object.entries(grouped).map(([cat,items])=><div key={cat}><strong className="small">{cat}</strong>{items.map(p=><button key={p.id} onClick={()=>setSelected(p.id)} style={{display:'block',width:'100%',textAlign:'left',margin:'6px 0',borderColor:selected===p.id?'#2463eb':undefined}}>{p.title}</button>)}</div>)}{q.data?.length===0&&<div className="empty">승인된 정책이 없습니다.</div>}</aside>{policy&&<article className="card"><div className="row between"><span className="badge APPROVED">APPROVED</span>{policy.has_conflict&&<span className="badge FAILED">⚠ CONFLICT</span>}</div><h1 style={{marginTop:16}}>{policy.title}</h1><p>{policy.summary}</p><h2>조건</h2>{policy.rules.map(r=><div className="rule" key={r.id}>• {r.content}</div>)}<h2>출처</h2>{policy.evidence.map(e=><div className="item" key={e.id}><strong>{e.source_type} · {e.source_name}</strong><div className="muted small">{e.source_path}:{e.start_line}-{e.end_line}</div></div>)}</article>}</div>
}

function Chat({id}:{id:string}){
 const [question,setQuestion]=useState(''); const [messages,setMessages]=useState<any[]>([]); const ask=useMutation({mutationFn:()=>api<any>(`/projects/${id}/chat`,{method:'POST',body:JSON.stringify({question})}),onSuccess:data=>{setMessages(m=>[...m,{question, ...data}]);setQuestion('')}});
 function submit(e:FormEvent){e.preventDefault();if(question.trim())ask.mutate()}
 return <div style={{maxWidth:850,margin:'0 auto'}}><div className="list">{messages.map((m,i)=><div className="card" key={i}><p><strong>Q.</strong> {m.question}</p><p style={{whiteSpace:'pre-wrap'}}>{m.answer}</p>{m.citations.length>0&&<><h3>출처</h3>{m.citations.map((c:any,j:number)=><div className="muted small" key={j}>{c.policy_title} · {c.source_path}:{c.lines}</div>)}</>}</div>)}{messages.length===0&&<div className="card empty">승인된 Policy에 대해 질문하세요. 근거가 없으면 답변하지 않습니다.</div>}</div><form className="card row" style={{marginTop:14}} onSubmit={submit}><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="선정된 캠페인을 언제 취소할 수 있어?"/><button className="primary" disabled={ask.isPending}>질문</button></form></div>
}
