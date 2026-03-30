import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { PasswordlessCard } from "@/components/auth/passwordless-card";

export default function PasswordlessPage() {
  return (
    <AuthScreenShell
      eyebrow="Passwordless"
      title="Support fast entry with magic links and phone OTP."
      description="This route isolates the passwordless flows so you can evolve OTP, magic link, and later wallet-first entry without rewriting session plumbing."
    >
      <PasswordlessCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
