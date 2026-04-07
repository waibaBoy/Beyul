"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";

type ProtectedSessionCardProps = {
  title?: string;
};

export const ProtectedSessionCard = ({ title = "Current session" }: ProtectedSessionCardProps) => {
  const { backendUser, isReady, session, user } = useAuth();

  if (isReady && !session) {
    return (
      <section className="auth-section">
        <h2>Sign in to continue</h2>
        <p>This page is only available once your account session is active.</p>
        <div className="button-row">
          <Link className="button-primary hero-link" href="/auth/sign-in">
            Sign in
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="auth-section">
      <h2>{title === "Current session" ? "Signed-in account" : title}</h2>
      <div className={`status-chip ${session ? "" : "offline"}`}>
        {isReady ? (session ? "Access ready" : "Signed out") : "Loading session"}
      </div>
      <dl className="kv-list">
        <div>
          <dt>Name</dt>
          <dd>{backendUser?.display_name ?? user?.user_metadata?.display_name ?? "Unknown"}</dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd>{user?.email ?? "Unavailable"}</dd>
        </div>
        <div>
          <dt>Role</dt>
          <dd>{backendUser?.is_admin ? "Admin" : "Member"}</dd>
        </div>
      </dl>
      <div className="button-row">
        <Link className="button-secondary hero-link" href="/auth/account">
          Account
        </Link>
        <Link className="button-secondary hero-link" href="/portfolio">
          Portfolio
        </Link>
      </div>
    </section>
  );
};
