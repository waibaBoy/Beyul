"use client";

import { useAuth } from "@/components/auth/auth-provider";

export const AuthSessionCard = () => {
  const { isReady, session, user } = useAuth();

  return (
    <section className="auth-section">
      <h2>Current session</h2>
      <div className={`status-chip ${session ? "" : "offline"}`}>
        {isReady ? (session ? "Session active" : "No session yet") : "Loading session"}
      </div>

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
    </section>
  );
};
