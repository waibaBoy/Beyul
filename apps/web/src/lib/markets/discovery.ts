import type { Market } from "@/lib/api/types";

export const MARKET_DISCOVERY_CATEGORIES = [
  "Trending",
  "Sports",
  "Politics",
  "Crypto",
  "Business",
  "World"
] as const;

export type MarketDiscoveryCategory = (typeof MARKET_DISCOVERY_CATEGORIES)[number];

export const isMarketDiscoveryCategory = (value: string | null): value is MarketDiscoveryCategory =>
  value !== null && (MARKET_DISCOVERY_CATEGORIES as readonly string[]).includes(value);

const CATEGORY_KEYWORDS: Record<Exclude<MarketDiscoveryCategory, "Trending">, RegExp> = {
  Sports: /\b(sport|sports|nrl|afl|cricket|rugby|soccer|football|tennis|nba|nfl|olympic|f1|formula 1)\b/i,
  Politics: /\b(politic|election|pm|prime minister|labor|liberal|albanese|coalition|senate|parliament|vote)\b/i,
  Crypto: /\b(btc|bitcoin|eth|ethereum|solana|crypto|memecoin|stablecoin|token)\b/i,
  Business: /\b(stock|stocks|asx|nasdaq|s&p|earnings|company|companies|tesla|apple|nvidia|bank|rate cut)\b/i,
  World: /\b(world|global|china|us|usa|america|europe|uk|war|geopolitic|trade deal)\b/i
};

const buildSearchText = (market: Market) =>
  [
    market.title,
    market.question,
    market.description,
    market.community_name,
    market.community_slug
  ]
    .filter(Boolean)
    .join(" ");

export const getMarketDiscoveryCategory = (market: Market): MarketDiscoveryCategory => {
  const haystack = buildSearchText(market);

  for (const [category, pattern] of Object.entries(CATEGORY_KEYWORDS) as Array<
    [Exclude<MarketDiscoveryCategory, "Trending">, RegExp]
  >) {
    if (pattern.test(haystack)) {
      return category;
    }
  }

  return "World";
};

export const getMarketVolumeValue = (market: Market) => {
  const parsed = Number(market.traded_volume ?? "0");
  return Number.isFinite(parsed) ? parsed : 0;
};

export const sortMarketsByVolume = (markets: Market[]) =>
  [...markets].sort((left, right) => {
    const volumeDelta = getMarketVolumeValue(right) - getMarketVolumeValue(left);
    if (volumeDelta !== 0) {
      return volumeDelta;
    }

    return Date.parse(right.updated_at) - Date.parse(left.updated_at);
  });

export const filterMarketsByDiscoveryCategory = (
  markets: Market[],
  category: MarketDiscoveryCategory
) => {
  if (category === "Trending") {
    return sortMarketsByVolume(markets);
  }

  return sortMarketsByVolume(markets).filter((market) => getMarketDiscoveryCategory(market) === category);
};
