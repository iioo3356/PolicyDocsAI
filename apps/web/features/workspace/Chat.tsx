"use client";

import { api, Policy } from "@/lib/api";
import type { ChatReply } from "@/domain/ChatReply";
import type { ChatMessage } from "@/domain/ChatMessage";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";

export function Chat({ id }: { id: string }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [policyId, setPolicyId] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const policies = useQuery({
    queryKey: ["policies", id],
    queryFn: () => api<Policy[]>(`/projects/${id}/policies?status=APPROVED`),
  });
  const ask = useMutation({
    mutationFn: (submitted: string) => api<ChatReply>(`/projects/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({
        question: submitted,
        policy_id: policyId || null,
        history: messages.slice(-4).flatMap(message => [
          { role: "user", content: message.question },
          { role: "assistant", content: message.answer.slice(0, 6000) },
        ]),
      }),
    }),
    onSuccess: (data, submitted) => {
      setMessages(current => [...current, { question: submitted, ...data }]);
      setQuestion("");
      if (data.related_policies.length === 1) setPolicyId(data.related_policies[0].id);
    },
  });
  const busy = ask.isPending;
  useEffect(() => { bottom.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [messages, ask.isPending]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim().length >= 2 && !busy) ask.mutate(question.trim());
  }

  return (
    <div className="policy-chat">
      <div className="chat-context">
        <label htmlFor="chat-policy">대상 정책</label>
        <select id="chat-policy" value={policyId} disabled={busy || policies.isPending}
          onChange={event => setPolicyId(event.target.value)}>
          <option value="">전체 승인 정책에서 찾기</option>
          {policies.data?.map(policy => <option key={policy.id} value={policy.id}>{policy.title}</option>)}
        </select>
        <p className="muted small">승인된 정책을 근거로 답합니다. 정책을 바꾸려면 관련 소스를 업데이트하고 변경안을 승인해 주세요.</p>
        <Link href={`/projects/${id}/sources`}>소스 추가·업데이트 →</Link>
        {policies.isError && <p role="alert">정책 목록을 불러오지 못했습니다. {policies.error.message}</p>}
      </div>
      <div className="chat-messages" role="log" aria-label="정책 대화" aria-live="polite">
        {messages.length === 0 && <div className="card empty">
          <h3>정책에 대해 질문해 보세요</h3>
          <p>“취소할 수 있는 조건이 뭐야?”</p>
          <p>변경이 필요하면 <Link href={`/projects/${id}/sources`}>관련 소스 추가·업데이트</Link>로 이동하세요.</p>
        </div>}
        {messages.map((message, index) => <div className="card chat-message" key={index}>
          <p className="chat-question"><strong>나</strong> {message.question}</p>
          <p className="chat-answer">{message.answer}</p>
          {message.action === "update_source" && <div className="chat-citations">
            {message.source_suggestions.map(item => <p key={`${item.source_id}-${item.policy_id}`}>
              <Link href={`/projects/${id}/sources?replace_source_id=${item.source_id}`}>
                {item.policy_title} · {item.source_name} 업데이트 →
              </Link>
            </p>)}
            {!message.source_suggestions.length && <Link href={`/projects/${id}/sources`}>관련 소스 추가 →</Link>}
          </div>}
          {message.citations.length > 0 && <div className="chat-citations">
            <h3>답변 근거</h3>
            {message.citations.map((citation, number) => <button type="button" key={number}
              disabled={busy} onClick={() => setPolicyId(citation.policy_id)}>
              {citation.policy_title} · {citation.source_path}{citation.lines ? `:${citation.lines}` : ""}
            </button>)}
          </div>}
        </div>)}
        {ask.isPending && <p role="status" className="muted">정책을 확인하고 있습니다…</p>}
        <div ref={bottom} />
      </div>
      {ask.isError && <p role="alert" className="chat-error">{ask.error.message}</p>}
      <form className="chat-compose" onSubmit={submit}>
        <label className="small" htmlFor="chat-question">정책 질문</label>
        <textarea id="chat-question" value={question} disabled={busy} maxLength={2000}
          onChange={event => setQuestion(event.target.value)} placeholder="궁금한 정책이나 변경이 필요한 정책을 알려주세요." />
        <button className="primary" disabled={busy || question.trim().length < 2}>
          {ask.isPending ? "처리 중…" : "보내기"}
        </button>
      </form>
    </div>
  );
}
