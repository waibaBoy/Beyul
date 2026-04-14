import type { Metadata } from "next";
import { PRIVACY_DOCUMENT_VERSION } from "@/lib/legal/compliance-copy";

export const metadata: Metadata = {
  title: "Privacy Policy (draft) · Satta",
  description: "Draft privacy policy — legal review required before production use."
};

export default function PrivacyPage() {
  return (
    <>
      <h1>Privacy Policy (draft)</h1>
      <p className="legal-doc-meta">Document version: {PRIVACY_DOCUMENT_VERSION}</p>
      <p>
        This is a <strong>placeholder draft</strong>. Replace with a policy that matches your real data flows (Supabase
        Auth, hosting, analytics, payment processors, logs, and cross-border transfers).
      </p>
      <h2>1. What we collect</h2>
      <p>
        Typical categories include account identifiers (email, phone if used), profile fields you submit, technical
        logs, and usage data required to operate the service securely.
      </p>
      <h2>2. Why we use it</h2>
      <p>To provide and secure the platform, comply with law, and improve reliability. Counsel will map APPs / GDPR / NZPA if relevant.</p>
      <h2>3. Your choices</h2>
      <p>Describe access, correction, deletion, marketing opt-out, and complaint channels as implemented.</p>
      <h2>4. Contact</h2>
      <p>Insert privacy contact details for your organisation.</p>
    </>
  );
}
