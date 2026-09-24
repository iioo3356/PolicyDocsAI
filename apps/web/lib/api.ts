export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export async function api<T>(path:string, init?:RequestInit):Promise<T> {
 const response = await fetch(`${API}${path}`, {...init, headers:init?.body instanceof FormData ? init.headers : {"Content-Type":"application/json",...init?.headers}});
 if (!response.ok) throw new Error((await response.json().catch(()=>null))?.detail ?? "요청에 실패했습니다.");
 if (response.status === 204) return undefined as T;
 return response.json();
}
export type { Project } from "@/domain/Project";
export type { Source } from "@/domain/Source";
export type { Candidate } from "@/domain/Candidate";
export type { Policy } from "@/domain/Policy";

