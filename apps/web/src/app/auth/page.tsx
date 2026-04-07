import Link from "next/link";
import { AuthScreenShell } from "@/components/auth/auth-screen-shell";

const routes = [
  {
    href: "/auth/sign-up",
    title: "Create account",
    description: "Email/password sign-up with username, display name, and phone metadata."
  },
  {
    href: "/auth/sign-in",
    title: "Sign in",
    description: "Email/password and Google sign-in on one reusable route."
  },
  {
    href: "/auth/passwordless",
    title: "Passwordless",
    description: "Magic link and phone OTP flows using the shared callback pipeline."
  },
  {
    href: "/auth/phone/verify",
    title: "Verify phone OTP",
    description: "Dedicated OTP confirmation route with resend support and session completion."
  },
  {
    href: "/auth/account",
    title: "Account",
    description: "Open your account overview with balances, PnL context, and session controls."
  }
];

export default function AuthIndexPage() {
  return (
    <AuthScreenShell
      eyebrow="Auth Routes"
      title="Choose how you want to access Satta."
      description="Create an account, sign in, or use passwordless entry, then move straight into markets, communities, and your portfolio."
    >
      <section className="auth-grid-full">
        {routes.map((route) => (
          <Link className="auth-route-card" href={route.href} key={route.href}>
            <strong>{route.title}</strong>
            <span>{route.description}</span>
          </Link>
        ))}
      </section>
    </AuthScreenShell>
  );
}
