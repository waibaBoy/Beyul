"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";

type ProtectedSessionCardProps = {
  title?: string;
};

export const ProtectedSessionCard = ({ title = "Current session" }: ProtectedSessionCardProps) => {
  const { isReady, session, user } = useAuth();

  if (isReady && !session) {
    return (
      <section className="auth-section">
        <h2>{title}</h2>
        <p>You need an authenticated session before using this screen.</p>
        <div className="button-row">
          <Link className="button-primary hero-link" href="/auth/sign-in">
            Go to sign in
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="auth-section">
      <h2>{title}</h2>
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
      </dl>
    </section>
  );
};
