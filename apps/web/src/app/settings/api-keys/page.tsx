import { AppScreenShell } from "@/components/app/app-screen-shell";
import { ApiKeyWorkspace } from "@/components/app/api-key-workspace";

export const metadata = {
  title: "API Keys — Satta",
  description: "Manage your API keys for programmatic trading.",
};

export default function ApiKeysPage() {
  return (
    <AppScreenShell eyebrow="Settings" title="API Keys">
      <ApiKeyWorkspace />
    </AppScreenShell>
  );
}
