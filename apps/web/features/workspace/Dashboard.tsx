"use client";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";


export function Dashboard({id}:{id:string}){
 const q=useQuery({queryKey:["dashboard",id],queryFn:()=>api<any>(`/projects/${id}/dashboard`),refetchInterval:3000});
 const items=[['등록 Source',q.data?.source_count],['전체 Policy',q.data?.policy_count],['Review 필요',q.data?.review_count],['Conflict',q.data?.conflict_count]];
 return <div className="grid cards">{items.map(([label,value])=><div className="card" key={label as string}><div className="muted small">{label}</div><div className="stat">{value??'—'}</div></div>)}</div>
}
