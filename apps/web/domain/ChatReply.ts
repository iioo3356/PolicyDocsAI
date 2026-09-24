import type { Policy } from "./Policy";

export type ChatReply = {
  answer: string;
  grounded: boolean;
  action: "answer" | "clarify" | "update_source";
  related_policies: Policy[];
  citations: {
    policy_id: string;
    policy_title: string;
    source_path: string;
    lines: string;
    kind: "source" | "revision" | "policy";
    revision_id?: string | null;
  }[];
  source_suggestions: { source_id: string; source_name: string; policy_id: string; policy_title: string }[];
};
