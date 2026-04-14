"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { ResponsibleGamblingNotice } from "@/components/auth/responsible-gambling-notice";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { buildSignupComplianceMetadata } from "@/lib/legal/compliance-copy";

const defaultSignUp = {
  email: "",
  password: "",
  username: "",
  displayName: "",
  phone: ""
};

export const SignUpCard = () => {
  const { signUpWithPassword } = useAuth();
  const [form, setForm] = useState(defaultSignUp);
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Create a user with the identity fields you want persisted into profile metadata."
  );

  const canSubmit = useMemo(
    () =>
      Boolean(
        form.email.trim() &&
          form.password &&
          form.username.trim() &&
          form.displayName.trim() &&
          ageConfirmed &&
          termsAccepted
      ),
    [ageConfirmed, form.displayName, form.email, form.password, form.username, termsAccepted]
  );

  return (
    <section className="auth-section">
      <h2>Create your account</h2>
      <p>Set up your identity once so your profile, markets, and portfolio all stay connected.</p>

      <form
        className="auth-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!canSubmit) {
            return;
          }
          void runAction("Creating email/password account...", async () => {
            await signUpWithPassword({
              ...form,
              signupCompliance: buildSignupComplianceMetadata()
            });
            setStatusMessage("Sign-up request sent. Check your Supabase confirmation flow.");
          });
        }}
      >
        <div className="field">
          <label htmlFor="signup-email">Email</label>
          <input
            id="signup-email"
            autoComplete="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            autoComplete="new-password"
            type="password"
            placeholder="Create a password"
            value={form.password}
            onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="signup-username">Username</label>
          <input
            id="signup-username"
            placeholder="themorningstar"
            value={form.username}
            onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="signup-display-name">Display name</label>
          <input
            id="signup-display-name"
            placeholder="Akash Tamang"
            value={form.displayName}
            onChange={(event) => setForm((current) => ({ ...current, displayName: event.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="signup-phone">Phone number</label>
          <input
            id="signup-phone"
            autoComplete="tel"
            placeholder="+61400000000"
            value={form.phone}
            onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
          />
        </div>

        <ResponsibleGamblingNotice />

        <div className="checkbox-stack" role="group" aria-label="Eligibility and terms">
          <label className="checkbox-field">
            <input
              type="checkbox"
              data-testid="signup-age-confirm"
              checked={ageConfirmed}
              onChange={(event) => setAgeConfirmed(event.target.checked)}
            />
            <span>
              I confirm that I am <strong>18 years of age or older</strong> and legally allowed to use this service in
              my jurisdiction.
            </span>
          </label>
          <label className="checkbox-field">
            <input
              type="checkbox"
              data-testid="signup-terms-confirm"
              checked={termsAccepted}
              onChange={(event) => setTermsAccepted(event.target.checked)}
            />
            <span>
              I have read and agree to the{" "}
              <Link href="/legal/terms" target="_blank" rel="noopener noreferrer">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link href="/legal/privacy" target="_blank" rel="noopener noreferrer">
                Privacy Policy
              </Link>
              .
            </span>
          </label>
        </div>

        <div className="button-row">
          <button className="button-primary" disabled={isSubmitting || !canSubmit} type="submit">
            Create account
          </button>
        </div>
      </form>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
