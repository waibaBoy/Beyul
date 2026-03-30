import Link from "next/link";

const surfaces = [
  {
    title: "Route-level auth screens",
    description: "Sign-in, sign-up, passwordless, and account are now split into reusable routes instead of a single catch-all panel."
  },
  {
    title: "Identity methods",
    description: "Email/password, phone OTP, magic link, and Google sign-in routed through one auth provider."
  },
  {
    title: "Backend compatibility",
    description: "Supabase access tokens can be sent directly to the FastAPI bearer auth layer you just wired."
  },
  {
    title: "Ready for app screens",
    description: "This auth slice can now be reused by market creation, feed posting, trading, and admin surfaces."
  }
];

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <div className="eyebrow">Satta Platform</div>
        <h1>Social market creation, moderation, and settlement flows on one stack.</h1>
        <p>
          Satta now has reusable auth, community feeds, market intake, and
          admin review surfaces sharing the same Supabase session and FastAPI
          bearer-token pipeline.
        </p>

        <div className="button-row hero-actions">
          <Link className="button-primary hero-link" href="/auth">
            Open auth routes
          </Link>
          <Link className="button-secondary hero-link" href="/communities">
            Open communities
          </Link>
          <Link className="button-secondary hero-link" href="/market-requests">
            Open market requests
          </Link>
          <Link className="button-secondary hero-link" href="/admin/review">
            Open admin review
          </Link>
          <Link className="button-secondary hero-link" href="/auth/account">
            Verify backend identity
          </Link>
        </div>

        <div className="grid">
          {surfaces.map((surface) => (
            <article className="card" key={surface.title}>
              <strong>{surface.title}</strong>
              <span>{surface.description}</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
