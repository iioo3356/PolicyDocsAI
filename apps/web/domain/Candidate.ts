import type { Policy } from "./Policy";
export type Candidate={id:string;proposed_policy_id?:string|null;previous_source_id?:string|null;related_policies?:Policy[];title:string;summary:string;category:string;rules:string[];confidence:number;source_id:string;source_path?:string;start_line?:number;end_line?:number;excerpt?:string;source_type?:string;source_name?:string};
