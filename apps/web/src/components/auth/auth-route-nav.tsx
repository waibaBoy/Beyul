"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export const AuthRouteNav = () => {
  const pathname = usePathname();

  if (pathname === "/auth/account") {
    return (
      <nav className="auth-route-nav" aria-label="Authentication routes">
        <Link className="auth-route-link" href="/markets">
          ← Back to markets
        </Link>
      </nav>
    );
  }

  return (
    <nav className="auth-route-nav" aria-label="Authentication routes">
      {pathname !== "/auth/sign-in" && (
        <Link className="auth-route-link auth-route-link-primary" href="/auth/sign-in">
          Sign in
        </Link>
      )}
      {pathname !== "/auth/sign-up" && (
        <Link className="auth-route-link auth-route-link-primary" href="/auth/sign-up">
          Create account
        </Link>
      )}
    </nav>
  );
};
