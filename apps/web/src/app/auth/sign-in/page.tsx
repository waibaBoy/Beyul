import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { SignInCard } from "@/components/auth/sign-in-card";

export default function SignInPage() {
  return (
    <AuthScreenShell
      eyebrow="Sign In"
      title="Sign in to trade, follow markets, and manage your account."
      description="Use the sign-in method you prefer, then continue straight into the market board, portfolio, and communities."
    >
      <SignInCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
