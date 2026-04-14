import {
  BETSTOP_INFO_URL,
  GAMBLING_HELP_ONLINE_URL,
  GAMBLING_HELPLINE_DISPLAY,
  GAMBLING_HELPLINE_HREF,
  RESPONSIBLE_WAGERING_HELP_URL
} from "@/lib/legal/compliance-copy";

/**
 * AU-facing harm-minimisation copy (draft). Replace with counsel-approved wording.
 */
export const ResponsibleGamblingNotice = () => {
  return (
    <aside className="signup-rg-panel" aria-labelledby="signup-rg-heading">
      <h3 id="signup-rg-heading" className="signup-rg-heading">
        Important information (Australia)
      </h3>
      <p>
        <strong>Gambling risk.</strong> Only wager what you can afford to lose. Do not chase losses. Odds do not
        guarantee outcomes.
      </p>
      <p>
        <strong>Age restriction.</strong> This service is intended for people aged <strong>18 years or older</strong>{" "}
        in Australia, where lawful.
      </p>
      <p>
        <strong>Help is free and confidential, 24/7.</strong> National Gambling Helpline:{" "}
        <a href={GAMBLING_HELPLINE_HREF} rel="noopener noreferrer">
          {GAMBLING_HELPLINE_DISPLAY}
        </a>
        . Online support:{" "}
        <a href={GAMBLING_HELP_ONLINE_URL} target="_blank" rel="noopener noreferrer">
          Gambling Help Online
        </a>
        .
      </p>
      <p>
        <strong>Self-exclusion (licensed Australian wagering).</strong>{" "}
        <a href={BETSTOP_INFO_URL} target="_blank" rel="noopener noreferrer">
          BetStop — the National Self-Exclusion Register
        </a>{" "}
        (Australian Government initiative for licensed online and phone wagering providers).
      </p>
      <p>
        Further resources:{" "}
        <a href={RESPONSIBLE_WAGERING_HELP_URL} target="_blank" rel="noopener noreferrer">
          Responsible Wagering Australia — Get help
        </a>
        .
      </p>
      <p className="signup-rg-disclaimer">
        Draft notice for product development only — not legal advice. Have counsel review all legal and compliance
        text before launch.
      </p>
    </aside>
  );
};
