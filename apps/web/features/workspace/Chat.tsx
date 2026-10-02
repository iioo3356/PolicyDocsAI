"use client";

import { api, Policy } from "@/lib/api";
import { streamChat } from "@/lib/chat-stream";
import type { ChatMessage } from "@/domain/ChatMessage";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowUp, BookOpen, LoaderCircle, Sparkles, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ChatAnswer } from "./ChatAnswer";
import Link from "next/link";

const suggestions = ["취소할 수 있는 조건을 알려줘", "환불 정책을 요약해줘", "정책을 변경하려면 어떻게 해야 해?"];

export function Chat({ id }: { id: string }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const policies = useQuery({
    queryKey: ["policies", id],
    queryFn: () => api<Policy[]>(`/projects/${id}/policies?status=APPROVED`),
  });
  const ask = useMutation({
    mutationFn: (submitted: string) => {
      controller.current = new AbortController();
      return streamChat(`/projects/${id}/chat`, JSON.stringify({
        question: submitted,
        policy_id: policyId || null,
        history: messages.slice(-4).flatMap(message => [
          { role: "user", content: message.question },
          { role: "assistant", content: message.answer.slice(0, 6000) },
        ]),
      }), controller.current.signal, text => setStreamedAnswer(current => current + text));
    },
    onSuccess: (data, submitted) => {
      setMessages(current => [...current, { question: submitted, ...data }]);
      setQuestion("");
      setSubmittedQuestion("");
      setStreamedAnswer("");
      if (data.related_policies.length === 1) setPolicyId(data.related_policies[0].id);
    },
    onError: () => { setSubmittedQuestion(""); setStreamedAnswer(""); },
    onSettled: () => requestAnimationFrame(() => input.current?.focus()),
  });
  const busy = ask.isPending;
  useEffect(() => { bottom.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [messages, busy, streamedAnswer]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim().length >= 2 && !busy) {
      setStreamedAnswer("");
      setSubmittedQuestion(question.trim());
      ask.mutate(question.trim());
    }
  }

  return (
    <div className="policy-chat">
      <header className="chat-toolbar">
        <div className="chat-identity"><span className="chat-avatar"><Sparkles size={18} /></span>
          <div><strong className="type-subheading">Policy AI</strong><span className="muted type-caption">승인된 정책을 바탕으로 답변합니다</span></div>
        </div>
        <Button type="button" variant="ghost" size="sm" disabled={busy || !messages.length}
          onClick={() => { setMessages([]); setPolicyId(""); setQuestion(""); ask.reset(); input.current?.focus(); }}>
          <RotateCcw size={14} /> 새 대화
        </Button>
      </header>
      <div className="chat-context">
        <label htmlFor="chat-policy"><BookOpen size={14} /> 대상 정책</label>
        <select id="chat-policy" value={policyId} disabled={busy || policies.isPending}
          onChange={event => setPolicyId(event.target.value)}>
          <option value="">전체 승인 정책에서 찾기</option>
          {policies.data?.map(policy => <option key={policy.id} value={policy.id}>{policy.title}</option>)}
        </select>
      </div>
      {policies.isError && <p role="alert" className="chat-error type-caption">정책 목록을 불러오지 못했습니다. {policies.error.message}</p>}
      <div className="chat-messages" role="log" aria-label="정책 대화" aria-live="polite" aria-busy={busy}>
        {messages.length === 0 && !busy && <div className="chat-welcome">
          <span className="chat-welcome-icon"><Sparkles size={28} /></span>
          <Badge variant="secondary">근거와 함께 찾는 답변</Badge>
          <h3 className="type-heading">어떤 정책이 궁금하세요?</h3>
          <p className="type-body">복잡한 업무 규칙을 물어보세요.<br />답변과 함께 관련 정책의 근거를 확인할 수 있어요.</p>
          <div className="chat-suggestions">{suggestions.map(text => <Button key={text} type="button" variant="outline"
            onClick={() => { setQuestion(text); input.current?.focus(); }}>{text}<ArrowUp size={14} /></Button>)}</div>
        </div>}
        {messages.map((message, index) => <div className="chat-turn" key={index}>
          <div className="chat-user type-body"><span className="sr-only">나: </span>{message.question}</div>
          <ChatAnswer message={message} id={id} busy={busy} onSelectPolicy={setPolicyId} />
        </div>)}
        {busy && <div className="chat-turn">
          <div className="chat-user type-body"><span className="sr-only">나: </span>{submittedQuestion}</div>
          {streamedAnswer && <article className="chat-assistant">
            <div className="chat-assistant-label type-caption"><Sparkles size={16} /><strong>Policy AI</strong></div>
            <p className="chat-answer type-body">{streamedAnswer}</p>
          </article>}
          <div role="status" className="chat-thinking type-caption"><LoaderCircle size={16} className="animate-spin" />{streamedAnswer ? "답변을 작성하고 있어요…" : "정책과 근거를 확인하고 있어요…"}</div>
        </div>}
        <div ref={bottom} />
      </div>
      <footer className="chat-footer">
        {ask.isError && <p role="alert" className="chat-error type-caption">{ask.error.message} 입력한 질문을 다시 보낼 수 있습니다.</p>}
        <form className="chat-compose" onSubmit={submit}>
          <label className="sr-only" htmlFor="chat-question">정책 질문</label>
          <Textarea className="min-h-[50px] rounded-none border-0 bg-transparent p-1 shadow-none focus-visible:ring-0" ref={input} id="chat-question" value={question} disabled={busy} maxLength={2000} rows={2}
            onChange={event => setQuestion(event.target.value)} placeholder="정책에 대해 무엇이든 물어보세요"
            onKeyDown={event => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault(); event.currentTarget.form?.requestSubmit();
              }
            }} />
          <div className="chat-compose-actions"><span>{question.length} / 2,000</span>
            <Button type="submit" size="icon" aria-label="질문 보내기" disabled={busy || question.trim().length < 2}>
              {busy ? <LoaderCircle className="animate-spin" /> : <ArrowUp />}
            </Button>
          </div>
        </form>
        <p className="chat-hint type-caption">Enter로 전송 · Shift+Enter로 줄바꿈 <span>정책 변경은 <Link href={`/projects/${id}/sources`}>소스 업데이트</Link> 후 승인해 주세요.</span></p>
      </footer>
    </div>
  );
}
