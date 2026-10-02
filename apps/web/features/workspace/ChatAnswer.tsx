import type { ChatMessage } from "@/domain/ChatMessage";
import { Button } from "@/components/ui/button";
import { Sparkles, FileText, ArrowUpRight } from "lucide-react";
import Link from "next/link";

export function ChatAnswer({ message, id, busy, onSelectPolicy }: {
  message: ChatMessage;
  id: string;
  busy: boolean;
  onSelectPolicy: (id: string) => void;
}) {
  return <article className="chat-assistant">
    <div className="chat-assistant-label type-caption"><Sparkles size={16} /><strong>Policy AI</strong></div>
    <p className="chat-answer type-body">{message.answer}</p>
    {message.action === "update_source" && <div className="chat-source-links">
      {message.source_suggestions.map(item => <Button asChild variant="outline" size="sm" key={`${item.source_id}-${item.policy_id}`}>
        <Link href={`/projects/${id}/sources?replace_source_id=${item.source_id}`}>
          {item.policy_title} · {item.source_name} 업데이트 <ArrowUpRight size={14} />
        </Link>
      </Button>)}
      {!message.source_suggestions.length && <Button asChild variant="outline" size="sm">
        <Link href={`/projects/${id}/sources`}>관련 소스 추가 <ArrowUpRight size={14} /></Link>
      </Button>}
    </div>}
    {message.citations.length > 0 && <div className="chat-citations">
      <h3 className="type-caption"><FileText size={13} /> 답변 근거 · 클릭하면 해당 정책으로 다음 질문을 좁힙니다</h3>
      {message.citations.map((citation, number) => <Button type="button" variant="outline" size="sm" className="h-auto min-h-16 max-w-full items-start justify-start gap-2 whitespace-normal px-3 py-3 text-left has-[>svg]:px-3" key={number}
        disabled={busy} onClick={() => onSelectPolicy(citation.policy_id)}>
        <FileText size={14} className="mt-0.5" /><span className="min-w-0"><span className="type-caption block">{citation.policy_title}</span><small className="type-caption mt-1 block break-all">{citation.source_path}{citation.lines ? `:${citation.lines}` : ""}</small></span>
      </Button>)}
    </div>}
  </article>;
}
