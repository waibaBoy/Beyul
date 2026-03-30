"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";

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
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Create a user with the identity fields you want persisted into profile metadata."
  );

  return (
    <section className="auth-section">
      <h2>Email sign up</h2>
      <p>Start with email/password and attach username, display name, and phone metadata at sign-up time.</p>

      <form
        className="auth-form"
        onSubmit={(event) => {
          event.preventDefault();
          void runAction("Creating email/password account...", async () => {
            await signUpWithPassword(form);
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
        <div className="button-row">
          <button className="button-primary" disabled={isSubmitting} type="submit">
            Create account
          </button>
        </div>
      </form>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
