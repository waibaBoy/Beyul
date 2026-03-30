import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { PhoneVerifyCard } from "@/components/auth/phone-verify-card";

export default function PhoneVerifyPage() {
  return (
    <AuthScreenShell
      eyebrow="Phone Verify"
      title="Finish passwordless phone sign-in with the OTP code."
      description="Use this route to confirm the SMS code, establish a session, and then continue into authenticated Satta screens."
    >
      <PhoneVerifyCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
