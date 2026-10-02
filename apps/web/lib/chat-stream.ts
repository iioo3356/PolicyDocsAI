import { API } from "./api";
import type { ChatReply } from "@/domain/ChatReply";

export async function streamChat(path: string, body: string, signal: AbortSignal, onDelta: (text: string) => void): Promise<ChatReply> {
  const response = await fetch(`${API}${path}/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body, signal,
  });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "요청에 실패했습니다.");
  if (!response.body) throw new Error("스트리밍 응답을 받을 수 없습니다.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let newline;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (!line) continue;
        const event = JSON.parse(line);
        if (event.type === "delta") onDelta(event.text);
        else if (event.type === "done") return event.response as ChatReply;
        else if (event.type === "error") throw new Error(event.message);
        else throw new Error("알 수 없는 스트리밍 응답입니다.");
      }
      if (done) throw new Error("응답이 중단되었습니다. 다시 질문해 주세요.");
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
