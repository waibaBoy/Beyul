import type { ReactNode } from "react";
import { AppRouteNav } from "@/components/app/app-route-nav";

type AppScreenShellProps = {
  children: ReactNode;
  eyebrow?: string;
  title?: string;
  description?: string;
};

export const AppScreenShell = ({ children, eyebrow, title, description }: AppScreenShellProps) => {
  const heading = eyebrow ?? title;
  const subtitle = eyebrow ? title : description;
  const hasHeader = Boolean(heading);

  return (
    <div className="app-shell">
      <AppRouteNav />
      <main className="app-main">
        {hasHeader && (
          <div className="app-page-header">
            <h1 className="app-page-title">{heading}</h1>
            {subtitle && <p className="app-page-desc">{subtitle}</p>}
          </div>
        )}
        <div style={{ display: "grid", gap: "16px" }}>{children}</div>
      </main>
    </div>
  );
};
