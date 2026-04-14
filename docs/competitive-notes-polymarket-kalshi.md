# Competitive notes: Polymarket vs Kalshi vs Satta

Living document: add sources, dates, and “we do / we don’t” as you validate the product. Not legal or investment advice.

## Positioning snapshot

| Dimension | Polymarket (typical) | Kalshi (typical) | Satta direction (from product vision) |
|-----------|----------------------|------------------|----------------------------------------|
| Jurisdiction / model | Crypto-native, global-leaning (with geo friction in practice) | US-regulated event contracts (CFTC path) | AU-first narrative; hybrid rails in schema |
| Liquidity | Deep global CLOB + incentives | Exchange-style books, retail + pro | P2P / community + friends seed liquidity |
| Creation | Curated / permissioned listing historically; community markets exist | Exchange-listed series | Anyone proposes → admin/community approve |
| Settlement | On-chain + oracle (e.g. UMA) narrative strong | Central clearing / rulebook | On-chain + oracle emphasis in architecture docs |

Use this table to avoid copying the wrong competitor: **Kalshi’s regulatory story is not copy-pasteable** without the same licences; **Polymarket’s liquidity story** is hard without global flow—your **group + creator rewards** wedge is different on purpose.

---

## Polymarket-shaped features (what “feels like Polymarket”)

**Discovery & retention**

- [ ] Category / topic taxonomy (politics, crypto, sports, macro) + trending / new / ending soon
- [ ] Search that scales (markets + users + communities)
- [ ] Activity feed: trades, new markets, large positions (privacy-aware)
- [ ] Watchlist + alerts (price, resolution date, outcome threshold)
- [ ] Share cards / OG images for markets (social growth loop)

**Trading & liquidity**

- [ ] Clear order book depth + spread + last trade (you have shells; polish vs “pro” terminals)
- [ ] One-click or suggested prices from mid / best bid-offer
- [ ] Market orders where the engine supports it (with slippage warnings)
- [ ] Liquidity rewards or “maker points” (aligns with your **0% maker** story)
- [ ] Resolution countdown + oracle status surfaced to **traders**, not only admins

**Trust & transparency**

- [ ] Market rule text + changelog + “what resolves YES” examples
- [ ] On-chain link per market (contract, pool, explorer) when `onchain` rail
- [ ] Historical volume / OI charts beyond sparklines

**Social**

- [ ] Comments or “arguments” thread per market (moderation heavy)
- [ ] Profiles visible to others (public PnL optional—careful with toxicity)

---

## Kalshi-shaped features (what “feels like Kalshi”)

**Retail trust & clarity**

- [ ] Plain-language rule summary + “max loss / max gain” calculator per contract
- [ ] Education hub: how contracts work, fees, resolution, **not** financial advice
- [ ] Prominent help, limits, self-exclusion cross-links (you started AU RG at signup)

**Product structure**

- [ ] Series / recurring events (e.g. “monthly CPI”) with templated creation
- [ ] Corporate actions style notices (rule clarifications, postponements)

**Pro / power users**

- [ ] Export history (CSV), API keys for read-only then trading
- [ ] Keyboard shortcuts, dense “pro” layout toggle

**Compliance posture (product, not only code)**

- [ ] Jurisdiction and eligibility copy per surface (signup, deposit, trade)
- [ ] Audit trail for rule changes and admin actions (you have admin paths to extend)

---

## Cross-cutting (both ecosystems care)

- [ ] **Mobile** web PWA or native apps (huge share of engagement)
- [ ] **Notifications**: email + push for fills, resolution, comments
- [ ] **Stablecoin / fiat on-ramp** story: clear who custodies what and when it hits chain
- [ ] **Fees page** synced with code (`about-platform.ts` + ledger)
- [ ] **Creator volume rebate** tiers (published numbers + in-app progress)
- [ ] **API** for markets, quotes, orders (read-first) for ecosystem bots
- [ ] **Status page** + incident comms (trust at scale)

---

## What not to copy blindly

- **Kalshi’s regulatory shell** without licences and legal stack
- **Polymarket’s global liquidity** as a day-one requirement—your **community P2P** story is a valid differentiator if execution is honest
- **Anonymous everything** vs your **moderated proposals**—different tradeoff, own it in copy

---

## Suggested research habits

1. **Screenshot flows** once per quarter: browse → market → trade → portfolio → resolve.
2. **Fee tables** and **rule PDFs**—save links in this doc under “References”.
3. **Note geo / KYC gates**—product implications, not envy.
4. For each feature above, tag: **MVP beta**, **v1**, **later**, **won’t do**.

## References (fill in as you go)

- Polymarket: `https://polymarket.com` — (add subpages you care about)
- Kalshi: `https://kalshi.com` — (add rulebook / fee schedule URLs)
- Internal: `docs/architecture.md` (Settlement and trust model), `/about` (user-facing)
