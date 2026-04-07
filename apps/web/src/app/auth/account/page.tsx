import { AccountCard } from "@/components/auth/account-card";
import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";

export default function AccountPage() {
  return (
    <AuthScreenShell
      eyebrow="Account"
      title="Review your account, PnL context, and session state."
      description="Use this screen as the quick account hub before jumping into your full portfolio or market activity."
    >
      <AccountCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
