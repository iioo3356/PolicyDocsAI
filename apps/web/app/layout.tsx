import "./globals.css";
import Link from "next/link";
import { Providers } from "./providers";
export const metadata = {title:"Policy Docs",description:"Traceable service policy intelligence"};
export default function Layout({children}:{children:React.ReactNode}) {
 return <html lang="ko"><body><Providers><div className="shell"><header className="topbar"><Link className="brand" href="/">Policy Docs</Link><span className="muted small">Source-grounded policy workspace</span></header>{children}</div></Providers></body></html>;
}

