"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";

export const AuthSessionCard = () => {
  const { backendUser, isReady, session, user } = useAuth();

  const displayName =
    backendUser?.display_name ?? user?.user_metadata?.display_name ?? "Guest";
  const userGlyph = displayName.charAt(0).toUpperCase();
  const isOnline = isReady && !!session;

  return (
    <section className="auth-section">
      <h2>Session</h2>

      <div className="acct-profile">
        <div className="acct-avatar">{userGlyph}</div>
        <div className="acct-info">
          <div className="acct-name">{displayName}</div>
          <div className="acct-handle">{user?.email ?? "Not signed in"}</div>
          <div className="acct-badges">
            <span className={`acct-status-dot ${isOnline ? "" : "offline"}`} />
            <span className={`acct-status-text ${isOnline ? "" : "offline"}`}>
              {!isReady ? "Loading…" : isOnline ? "Signed in" : "Signed out"}
            </span>
            {backendUser?.is_admin ? (
              <span className="acct-admin-badge">Admin</span>
            ) : null}
          </div>
        </div>
      </div>

      <dl className="kv-list">
        <div>
          <dt>Username</dt>
          <dd>{backendUser?.username ?? "—"}</dd>
        </div>
        <div>
          <dt>Account type</dt>
          <dd>{backendUser?.is_admin ? "Admin" : session ? "Member" : "Visitor"}</dd>
        </div>
      </dl>

      <div className="button-row">
        <Link className="button-secondary" href={session ? "/portfolio" : "/auth/sign-in"}>
          {session ? "Open portfolio" : "Sign in"}
        </Link>
        {session ? (
          <Link className="button-secondary" href="/auth/account">
            Account settings
          </Link>
        ) : null}
      </div>
    </section>
  );
};
