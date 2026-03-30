"use client";

import { useState } from "react";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";

type BackendUser = {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
};

export const AccountCard = () => {
  const { getAccessToken, session, signOut, user } = useAuth();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Use this screen to verify that the current Supabase session is accepted by FastAPI."
  );

  return (
    <section className="auth-section">
      <h2>Account + backend sync</h2>
      <p>This route is the single place to verify session state, sign out, and prove bearer token forwarding.</p>

      <dl className="kv-list">
        <div>
          <dt>User ID</dt>
          <dd>{user?.id ?? "Not signed in"}</dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd>{user?.email ?? "Unavailable"}</dd>
        </div>
        <div>
          <dt>Phone</dt>
          <dd>{user?.phone ?? "Unavailable"}</dd>
        </div>
      </dl>

      <div className="button-row">
        <button
          className="button-primary"
          disabled={isSubmitting || !session}
          onClick={() =>
            void runAction(
              "Syncing the current Supabase session with FastAPI...",
              async () => {
                const accessToken = await getAccessToken();
                const nextBackendUser = await beyulApiFetch<BackendUser>("/api/v1/auth/me", {
                  accessToken
                });
                setBackendUser(nextBackendUser);
                return nextBackendUser;
              },
              {
                successMessage: "FastAPI accepted the Supabase bearer token."
              }
            )
          }
        >
          Verify backend bearer auth
        </button>
        <button
          className="button-secondary"
          disabled={isSubmitting || !session}
          onClick={() => void runAction("Signing out...", signOut)}
        >
          Sign out
        </button>
      </div>

      <pre className="code-block">
        {backendUser ? JSON.stringify(backendUser, null, 2) : "No backend verification yet."}
      </pre>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
