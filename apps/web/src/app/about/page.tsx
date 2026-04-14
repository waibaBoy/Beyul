import type { Metadata } from "next";
import Link from "next/link";
import { AppRouteNav } from "@/components/app/app-route-nav";
import {
  PLATFORM_MAKER_FEE_PERCENT,
  PLATFORM_TAKER_FEE_PERCENT
} from "@/lib/product/about-platform";

export const metadata: Metadata = {
  title: "About Satta",
  description:
    "Community prediction markets: propose bets, trade with friends, fees and creator rewards explained."
};

export default function AboutPage() {
  return (
    <div className="app-shell">
      <AppRouteNav />
      <main className="about-page">
        <header className="about-hero">
          <p className="about-eyebrow">About Satta</p>
          <h1>Prediction markets built for groups—not only global order books.</h1>
          <p className="about-lead">
            Satta is a place to propose real-money style contracts, invite your circle to trade, and let the platform
            handle rules, fees, and settlement—while you keep the social energy of a group bet.
          </p>
        </header>

        <section className="about-section" aria-labelledby="about-what">
          <h2 id="about-what">What this is</h2>
          <p>
            Think <strong>Polymarket-style questions</strong> with a <strong>Kalshi-style</strong> appetite for clear
            outcomes—but organised around <strong>communities</strong> and <strong>peer liquidity</strong>: friends and
            members fund and trade the markets they care about, not only anonymous global depth.
          </p>
          <p>
            Operators and community moderators can <strong>review proposals</strong> before a market goes live, so spam
            and unsafe questions are filtered while still letting <strong>anyone propose</strong> a market, public or
            community-scoped.
          </p>
        </section>

        <section className="about-section" aria-labelledby="about-create">
          <h2 id="about-create">How you create a bet</h2>
          <ol className="about-steps">
            <li>
              <strong>Propose</strong> — Submit a market request with the question, outcomes, and timing.
            </li>
            <li>
              <strong>Review</strong> — Admins or community staff approve when it meets house rules.
            </li>
            <li>
              <strong>Liquidity</strong> — Creators and early participants seed the pool so others can trade.
            </li>
            <li>
              <strong>Trade</strong> — Members buy and sell outcome shares until trading closes.
            </li>
            <li>
              <strong>Resolve &amp; payout</strong> — The market settles; winners are paid according to the published
              rules.
            </li>
          </ol>
          <p>
            <Link href="/market-requests">Start a market request →</Link>
          </p>
        </section>

        <section className="about-section" aria-labelledby="about-fees">
          <h2 id="about-fees">Fees we are targeting</h2>
          <p>
            We want <strong>makers</strong> (people who rest orders that add liquidity) to pay <strong>nothing</strong>,
            and <strong>takers</strong> (people who trade against that liquidity) to pay a small, transparent fee—
            similar to how large venues reward liquidity providers.
          </p>
          <div className="about-fee-cards" role="list">
            <div className="about-fee-card" role="listitem">
              <span className="about-fee-label">Taker fee</span>
              <strong className="about-fee-value">{PLATFORM_TAKER_FEE_PERCENT}%</strong>
              <span className="about-fee-hint">Paid when your order removes liquidity from the book.</span>
            </div>
            <div className="about-fee-card" role="listitem">
              <span className="about-fee-label">Maker fee</span>
              <strong className="about-fee-value">{PLATFORM_MAKER_FEE_PERCENT}%</strong>
              <span className="about-fee-hint">Resting liquidity that gets filled pays no platform fee.</span>
            </div>
          </div>
          <p className="about-note">
            Exact fee handling in the ledger and matching engine will match these targets as we ship toward beta.
            Always check the fee line on each market before you trade.
          </p>
        </section>

        <section className="about-section" aria-labelledby="about-creator">
          <h2 id="about-creator">Creators earn when their market succeeds</h2>
          <p>
            If a market you created reaches <strong>certain trading volume milestones</strong>, you can receive a{" "}
            <strong>share of the platform fee</strong> collected on that market—not just bragging rights.
          </p>
          <p>
            Six tiers from <strong>Starter</strong> to <strong>Diamond</strong> unlock fee-share percentages from 0%
            to 50% as your cumulative market volume grows. Track your progress, see the full tier schedule, and
            compare against other creators on the{" "}
            <Link href="/creators">Creator dashboard</Link>.
          </p>
          <p>
            That aligns everyone: the platform earns on activity, and successful market builders who bring real volume
            get rewarded for growing healthy, liquid markets.
          </p>
        </section>

        <section className="about-section about-disclaimer" aria-labelledby="about-legal">
          <h2 id="about-legal">Before you trade</h2>
          <p>
            Markets involve financial risk. Read the <Link href="/legal/terms">Terms</Link> and{" "}
            <Link href="/legal/privacy">Privacy</Link> drafts, use responsible gambling resources linked at sign-up,
            and only participate where it is lawful for you.
          </p>
        </section>

        <p className="about-back">
          <Link href="/">← Back to home</Link>
        </p>
      </main>
    </div>
  );
}
