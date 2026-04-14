import type { ReactNode } from "react";
import Link from "next/link";

export default function LegalLayout({ children }: { children: ReactNode }) {
  return (
    <main className="legal-doc-shell">
      <header className="legal-doc-header">
        <Link href="/" className="legal-doc-back">
          ← Home
        </Link>
        <nav className="legal-doc-nav" aria-label="Legal documents">
          <Link href="/legal/terms">Terms</Link>
          <Link href="/legal/privacy">Privacy</Link>
        </nav>
      </header>
      <article className="legal-doc-article">{children}</article>
    </main>
  );
}
