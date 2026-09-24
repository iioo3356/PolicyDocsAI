import "./globals.css";
import "./workspace.css";
import "./chat.css";
import { Providers } from "./providers";

export const metadata = { title: "Policy Docs", description: "근거에서 시작하는 명확한 정책 문서" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body><Providers><div className="shell">{children}</div></Providers></body></html>;
}
