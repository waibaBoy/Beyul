import type { ReactNode } from "react";
import { AuthRouteNav } from "@/components/auth/auth-route-nav";

type AuthScreenShellProps = {
  children: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
};

export const AuthScreenShell = ({
  children,
  description,
  eyebrow,
  title
}: AuthScreenShellProps) => {
  return (
    <main className="auth-page">
      <section className="auth-hero">
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
        <AuthRouteNav />
      </section>

      <section className="auth-page-grid">{children}</section>
    </main>
  );
};
