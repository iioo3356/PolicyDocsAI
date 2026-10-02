import { cn } from "@/lib/utils";

export function PolicyDocsLogo({ compact = false }: { compact?: boolean }) {
  return <span className={cn("policy-logo", compact && "policy-logo-compact")}>
    <svg className="policy-logo-mark" viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <rect width="64" height="64" rx="19" fill="currentColor" />
      <path d="M17 17h20l10 10v20H17V17Z" stroke="white" strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M37 17v10h10M24 27h6M24 34h9" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="m28 42 4 4 10-11" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <span className="policy-logo-wordmark">Policy Docs<span className="policy-logo-caption">KNOWLEDGE WORKSPACE</span></span>
  </span>;
}
