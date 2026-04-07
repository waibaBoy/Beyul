import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { SignUpCard } from "@/components/auth/sign-up-card";

export default function SignUpPage() {
  return (
    <AuthScreenShell
      eyebrow="Sign Up"
      title="Create your Satta account and get ready to trade."
      description="Choose your email identity, username, and display name once, then use the same account across communities, markets, and portfolio."
    >
      <SignUpCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
