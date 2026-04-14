/**
 * Document version strings stored in Supabase user_metadata and mirrored to Postgres
 * `legal_acceptances` on first authenticated API request. Bump when counsel approves new drafts.
 */
export const LEGAL_BUNDLE_VERSION = "beyul-compliance-2026-04-11";
export const TERMS_DOCUMENT_VERSION = "terms-2026-04-11";
export const PRIVACY_DOCUMENT_VERSION = "privacy-2026-04-11";

export const GAMBLING_HELPLINE_DISPLAY = "1800 858 858";
export const GAMBLING_HELPLINE_HREF = "tel:1800858858";
export const GAMBLING_HELP_ONLINE_URL = "https://www.gamblinghelponline.org.au/";
export const BETSTOP_INFO_URL = "https://www.betstop.gov.au/";
export const RESPONSIBLE_WAGERING_HELP_URL = "https://responsiblewagering.com.au/get-help/";

export type SignupComplianceMetadata = {
  legal_bundle_version: string;
  terms_version: string;
  privacy_version: string;
  terms_accepted_at: string;
  age_confirmed: true;
};

export function buildSignupComplianceMetadata(): SignupComplianceMetadata {
  return {
    legal_bundle_version: LEGAL_BUNDLE_VERSION,
    terms_version: TERMS_DOCUMENT_VERSION,
    privacy_version: PRIVACY_DOCUMENT_VERSION,
    terms_accepted_at: new Date().toISOString(),
    age_confirmed: true
  };
}
