export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export async function api<T>(path:string, init?:RequestInit):Promise<T> {
 const response = await fetch(`${API}${path}`, {...init, headers:init?.body instanceof FormData ? init.headers : {"Content-Type":"application/json",...init?.headers}});
 if (!response.ok) throw new Error((await response.json().catch(()=>null))?.detail ?? "요청에 실패했습니다.");
 if (response.status === 204) return undefined as T;
 return response.json();
}
export type Project={id:string;name:string;description?:string;created_at:string};
export type Source={id:string;name:string;kind:string;role:string;status:string;error_message?:string;discovered_policy_count:number};
export type Candidate={id:string;title:string;summary:string;category:string;rules:string[];confidence:number;source_id:string;source_path?:string;start_line?:number;end_line?:number;excerpt?:string;source_type?:string;source_name?:string};
export type Policy={id:string;title:string;summary:string;category:string;status:string;confidence:number;has_conflict:boolean;rules:{id:string;content:string}[];evidence:{id:string;source_type:string;source_name:string;source_path:string;start_line:number;end_line:number;excerpt:string}[]};

