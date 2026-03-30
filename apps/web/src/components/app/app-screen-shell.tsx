import type { ReactNode } from "react";
import { AppRouteNav } from "@/components/app/app-route-nav";

type AppScreenShellProps = {
  children: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
};

export const AppScreenShell = ({ children, description, eyebrow, title }: AppScreenShellProps) => {
  return (
    <main className="auth-page">
      <section className="auth-hero">
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
        <AppRouteNav />
      </section>
      <section className="auth-page-grid">{children}</section>
    </main>
  );
};
