import { AccountCard } from "@/components/auth/account-card";
import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";

export default function AccountPage() {
  return (
    <AuthScreenShell
      eyebrow="Account"
      title="Inspect the current session and verify backend trust."
      description="Use this screen to prove that the Supabase access token generated on the frontend is accepted by the FastAPI bearer auth layer."
    >
      <AccountCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
