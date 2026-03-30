import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { SignUpCard } from "@/components/auth/sign-up-card";

export default function SignUpPage() {
  return (
    <AuthScreenShell
      eyebrow="Sign Up"
      title="Create a reusable identity foundation before markets and feeds."
      description="The sign-up route captures the identity fields the backend will later sync into profiles, communities, trading, and admin permissions."
    >
      <SignUpCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
