import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { PhoneVerifyCard } from "@/components/auth/phone-verify-card";

export default function PhoneVerifyPage() {
  return (
    <AuthScreenShell
      eyebrow="Phone Verify"
      title="Finish signing in with the code from your phone."
      description="Confirm the SMS code, activate your session, and continue into your account."
    >
      <PhoneVerifyCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
