import type { Metadata } from "next";
import { TERMS_DOCUMENT_VERSION } from "@/lib/legal/compliance-copy";

export const metadata: Metadata = {
  title: "Terms of Service (draft) · Satta",
  description: "Draft terms of service — legal review required before production use."
};

export default function TermsPage() {
  return (
    <>
      <h1>Terms of Service (draft)</h1>
      <p className="legal-doc-meta">Document version: {TERMS_DOCUMENT_VERSION}</p>
      <p>
        This is a <strong>placeholder draft</strong> for engineering and product scaffolding. It is not legal advice and
        does not form a binding agreement until replaced by counsel-approved terms and linked from your production
        signup flow.
      </p>
      <h2>1. The service</h2>
      <p>
        Satta provides software interfaces for community prediction markets. Features, availability, and jurisdictions
        may change. You are responsible for ensuring your use is lawful where you live.
      </p>
      <h2>2. Eligibility</h2>
      <p>
        You must be at least <strong>18 years old</strong> (or the age of majority in your jurisdiction, if higher) to
        register. You must provide accurate information and keep credentials secure.
      </p>
      <h2>3. Responsible use</h2>
      <p>
        Trading and wagering-style products carry financial risk. Set limits, take breaks, and seek help early if
        gambling stops feeling like entertainment. National Gambling Helpline (Australia):{" "}
        <a href="tel:1800858858">1800 858 858</a>.
      </p>
      <h2>4. Liability</h2>
      <p>
        To the extent permitted by the <em>Competition and Consumer Act 2010</em> (Cth) and other applicable law, service
        providers may limit liability for certain losses. Your lawyer will set out enforceable wording for your entity
        and product.
      </p>
      <h2>5. Contact</h2>
      <p>Insert support email or ticketing address after you incorporate.</p>
    </>
  );
}
