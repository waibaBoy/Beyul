"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";

export const SignInCard = () => {
  const { signInWithGoogle, signInWithPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Sign in with either email/password or Google."
  );

  return (
    <section className="auth-section">
      <h2>Sign in</h2>
      <p>Use the same Supabase session for frontend rendering and backend bearer-token requests.</p>

      <form
        className="auth-form"
        onSubmit={(event) => {
          event.preventDefault();
          void runAction("Signing in with email/password...", async () => {
            await signInWithPassword({ email, password });
            setStatusMessage("Signed in with email/password.");
          });
        }}
      >
        <div className="field">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            autoComplete="current-password"
            type="password"
            placeholder="Your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <div className="button-row">
          <button className="button-primary" disabled={isSubmitting} type="submit">
            Email sign in
          </button>
          <button
            className="button-secondary"
            disabled={isSubmitting}
            type="button"
            onClick={() =>
              void runAction("Starting Google sign-in...", async () => {
                await signInWithGoogle();
              })
            }
          >
            Continue with Google
          </button>
        </div>
      </form>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
