import type { ChatReply } from "./ChatReply";

export type ChatMessage = ChatReply & { question: string };
