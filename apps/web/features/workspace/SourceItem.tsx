"use client";
import { api,Source } from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";


export function SourceItem({source,roles,onChanged,onUpdate}:{source:Source;roles:string[];onChanged:()=>void;onUpdate:()=>void}){
 const [editing,setEditing]=useState(false); const [role,setRole]=useState(source.role);
 const save=useMutation({mutationFn:()=>api<Source>(`/sources/${source.id}/role`,{method:'PATCH',body:JSON.stringify({role})}),onSuccess:()=>{setEditing(false);onChanged()}});
 const remove=useMutation({mutationFn:()=>api<void>(`/sources/${source.id}`,{method:'DELETE'}),onSuccess:onChanged});
 function confirmDelete(){if(window.confirm(`'${source.name}' Source와 분석 결과를 삭제할까요?`))remove.mutate()}
 const busy=source.status==='PENDING'||source.status==='PROCESSING';
 return <div className="item"><div className="row between"><strong>{source.name}</strong><span className={`badge ${source.status}`}>{source.status}</span></div>{editing?<div className="row" style={{marginTop:10}}><input list={`roles-${source.id}`} value={role} onChange={e=>setRole(e.target.value)} autoFocus/><datalist id={`roles-${source.id}`}>{roles.map(item=><option value={item} key={item}/>)}</datalist><button className="primary" disabled={!role.trim()||save.isPending} onClick={()=>save.mutate()}>저장</button><button onClick={()=>{setRole(source.role);setEditing(false)}}>취소</button></div>:<div className="row between" style={{marginTop:8}}><span className="muted small">역할: {source.role} · {source.kind} · 발견 {source.discovered_policy_count}개</span><div className="row"><button className="small" disabled={source.status!=="COMPLETED"} onClick={onUpdate}>업데이트</button><button className="small" onClick={()=>setEditing(true)}>역할 변경</button><button className="danger small" disabled={busy||remove.isPending} title={busy?'분석이 끝난 뒤 삭제할 수 있습니다.':undefined} onClick={confirmDelete}>{remove.isPending?'삭제 중':busy?'분석 중':'삭제'}</button></div></div>}{busy&&<p className="muted small">분석 중에는 삭제할 수 없습니다. API 재시작으로 중단된 작업은 자동으로 실패 처리됩니다.</p>}{save.error&&<p style={{color:'#b42318'}} className="small">{save.error.message}</p>}{remove.error&&<p style={{color:'#b42318'}} className="small">{remove.error.message}</p>}{source.error_message&&<p style={{color:'#b42318'}}>{source.error_message}</p>}</div>
}
