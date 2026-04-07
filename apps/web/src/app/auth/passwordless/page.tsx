import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { PasswordlessCard } from "@/components/auth/passwordless-card";

export default function PasswordlessPage() {
  return (
    <AuthScreenShell
      eyebrow="Passwordless"
      title="Use magic links or phone OTP for faster access."
      description="Choose the fastest way back into your account without relying on a password."
    >
      <PasswordlessCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
