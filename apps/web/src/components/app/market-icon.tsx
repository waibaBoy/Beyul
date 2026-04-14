"use client";

import { useState } from "react";
import { useEffect } from "react";
import { getMarketDiscoveryCategory } from "@/lib/markets/discovery";
import type { Market } from "@/lib/api/types";

const CATEGORY_EMOJI: Record<string, string> = {
  Crypto: "🪙",
  Sports: "🏆",
  Politics: "🏛️",
  Business: "📈",
  World: "🌍",
  Trending: "🔮"
};

const KNOWN_CRYPTO_SYMBOLS = new Set([
  "BTC",
  "ETH",
  "SOL",
  "XRP",
  "BNB",
  "DOGE",
  "ADA",
  "AVAX",
  "DOT",
  "MATIC",
  "TRX",
  "LINK",
  "LTC",
  "BCH",
  "ATOM",
  "NEAR",
  "UNI",
  "APT",
  "ARB",
  "OP",
  "SUI",
  "PEPE",
  "SHIB",
  "TON",
  "ETC",
  "XLM",
  "FIL",
  "HBAR",
  "INJ",
  "AAVE",
  "MKR"
]);

const SYMBOL_ALIASES: Record<string, string> = {
  XBT: "btc"
};

const COIN_NAME_TO_SYMBOL: Record<string, string> = {
  bitcoin: "btc",
  ethereum: "eth",
  solana: "sol",
  ripple: "xrp",
  dogecoin: "doge",
  cardano: "ada",
  avalanche: "avax",
  polkadot: "dot",
  chainlink: "link",
  litecoin: "ltc",
  aptos: "apt",
  arbitrum: "arb",
  optimism: "op",
  sui: "sui",
  toncoin: "ton"
};

function normalizeCryptoSymbol(value: string): string | null {
  const cleaned = value.replace(/[^a-zA-Z0-9$]/g, "").trim();
  if (!cleaned) return null;

  const upper = cleaned.replace(/^\$/, "").toUpperCase();
  if (KNOWN_CRYPTO_SYMBOLS.has(upper)) return upper.toLowerCase();
  if (SYMBOL_ALIASES[upper]) return SYMBOL_ALIASES[upper];

  const lower = upper.toLowerCase();
  if (COIN_NAME_TO_SYMBOL[lower]) return COIN_NAME_TO_SYMBOL[lower];
  return null;
}

function resolveCryptoAssetSymbol(market: Market): string | null {
  const explicitAsset = market.reference_context?.reference_asset?.trim();
  if (explicitAsset) {
    const normalizedExplicit = normalizeCryptoSymbol(explicitAsset);
    if (normalizedExplicit) return normalizedExplicit;
  }

  const searchableText = [
    market.title,
    market.question,
    market.reference_context?.reference_label,
    market.reference_context?.reference_symbol
  ]
    .filter(Boolean)
    .join(" ")
    .toUpperCase();

  // Match "$BTC" first, then standalone tokens like "BTC".
  const dollarMatch = searchableText.match(/\$([A-Z0-9]{2,10})\b/);
  if (dollarMatch?.[1]) {
    const symbol = dollarMatch[1];
    const normalized = normalizeCryptoSymbol(symbol);
    if (normalized) return normalized;
  }

  const tokenMatches = searchableText.match(/\b[A-Z0-9]{2,10}\b/g) ?? [];
  for (const token of tokenMatches) {
    const normalized = normalizeCryptoSymbol(token);
    if (normalized) return normalized;
  }

  const normalizedText = searchableText.toLowerCase();
  for (const [coinName, symbol] of Object.entries(COIN_NAME_TO_SYMBOL)) {
    if (normalizedText.includes(coinName)) return symbol;
  }

  return null;
}

function deriveIconUrl(market: Market): string | null {
  if (market.image_url) return market.image_url;

  const asset = resolveCryptoAssetSymbol(market);

  // If we can confidently resolve a coin symbol, prefer its logo even when
  // category tagging is imperfect.
  if (asset) {
    return `https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@master/32/color/${asset}.png`;
  }

  const cat = getMarketDiscoveryCategory(market);

  const refUrl = market.settlement_reference_url;
  if (refUrl) {
    try {
      const domain = new URL(refUrl).hostname;
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
    } catch {
      return null;
    }
  }

  return null;
}

export function MarketIcon({ market, size = 36 }: { market: Market; size?: number }) {
  const [imgFailed, setImgFailed] = useState(false);
  const iconUrl = deriveIconUrl(market);
  const cat = getMarketDiscoveryCategory(market);
  const emoji = CATEGORY_EMOJI[cat] ?? "🔮";

  useEffect(() => {
    // If the resolved URL changes (e.g., better symbol detection), retry image load.
    setImgFailed(false);
  }, [iconUrl]);

  if (!iconUrl || imgFailed) {
    return (
      <span
        className="market-icon market-icon-emoji"
        style={{ width: size, height: size, fontSize: Math.round(size * 0.55) }}
        aria-hidden="true"
      >
        {emoji}
      </span>
    );
  }

  return (
    <img
      className="market-icon"
      src={iconUrl}
      alt=""
      width={size}
      height={size}
      onError={() => setImgFailed(true)}
    />
  );
}
