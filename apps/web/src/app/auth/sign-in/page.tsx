import { AuthScreenShell } from "@/components/auth/auth-screen-shell";
import { AuthSessionCard } from "@/components/auth/auth-session-card";
import { SignInCard } from "@/components/auth/sign-in-card";

export default function SignInPage() {
  return (
    <AuthScreenShell
      eyebrow="Sign In"
      title="Access Satta with the same Supabase session the API will trust."
      description="This route is for standard credential and Google sign-in. Once the session exists, the frontend can forward the access token directly to FastAPI."
    >
      <SignInCard />
      <AuthSessionCard />
    </AuthScreenShell>
  );
}
