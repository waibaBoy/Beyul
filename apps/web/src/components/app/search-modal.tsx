"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Community, Market } from "@/lib/api/types";

type PageResult = {
  kind: "page";
  id: string;
  label: string;
  description: string;
  href: string;
  tag: string;
};

type MarketResult = {
  kind: "market";
  id: string;
  label: string;
  description: string;
  href: string;
  tag: string;
};

type CommunityResult = {
  kind: "community";
  id: string;
  label: string;
  description: string;
  href: string;
  tag: string;
};

type AnyResult = PageResult | MarketResult | CommunityResult;

const PAGE_RESULTS: PageResult[] = [
  { kind: "page", id: "home", label: "Home", description: "Trending markets and discovery", href: "/", tag: "Page" },
  { kind: "page", id: "markets", label: "Markets", description: "Browse all open markets", href: "/markets", tag: "Page" },
  { kind: "page", id: "create", label: "Create a market", description: "Propose a new bet or prediction", href: "/market-requests", tag: "Page" },
  { kind: "page", id: "portfolio", label: "My portfolio", description: "Your positions, balances and orders", href: "/portfolio", tag: "Page" },
  { kind: "page", id: "communities", label: "Communities", description: "Topic-based market communities", href: "/communities", tag: "Page" },
  { kind: "page", id: "sign-in", label: "Sign in", description: "Log into your account", href: "/auth/sign-in", tag: "Auth" },
  { kind: "page", id: "sign-up", label: "Create account", description: "Register for free", href: "/auth/sign-up", tag: "Auth" },
  { kind: "page", id: "account", label: "Account settings", description: "Manage your profile and session", href: "/auth/account", tag: "Settings" },
  { kind: "page", id: "admin", label: "Admin review", description: "Moderate posts and market requests", href: "/admin/review", tag: "Admin" }
];

const CATEGORY_TAGS: Record<string, string> = {
  open: "Open",
  trading_paused: "Paused",
  settled: "Settled",
  cancelled: "Cancelled",
  pending_liquidity: "Pending"
};

function scoreMatch(text: string, query: string): number {
  const t = text.toLowerCase();
  const q = query.toLowerCase();
  if (t === q) return 3;
  if (t.startsWith(q)) return 2;
  if (t.includes(q)) return 1;
  return 0;
}

function filterAndScore<T extends { label: string; description: string }>(
  items: T[],
  query: string
): T[] {
  if (!query.trim()) return items;
  return items
    .map((item) => ({
      item,
      score: Math.max(scoreMatch(item.label, query), scoreMatch(item.description, query) * 0.5)
    }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .map(({ item }) => item);
}

type SearchModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export const SearchModal = ({ isOpen, onClose }: SearchModalProps) => {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const [query, setQuery] = useState("");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [communities, setCommunities] = useState<Community[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!isOpen) return;

    const loadData = async () => {
      try {
        const [nextMarkets, nextCommunities] = await Promise.allSettled([
          beyulApiFetch<Market[]>("/api/v1/markets"),
          beyulApiFetch<Community[]>("/api/v1/communities")
        ]);
        if (nextMarkets.status === "fulfilled") setMarkets(nextMarkets.value);
        if (nextCommunities.status === "fulfilled") setCommunities(nextCommunities.value);
      } catch {
        // non-critical: search still works for pages
      }
    };

    void loadData();
    setTimeout(() => inputRef.current?.focus(), 30);
  }, [isOpen]);

  useEffect(() => {
    setQuery("");
    setActiveIndex(0);
  }, [isOpen]);

  const marketResults: MarketResult[] = useMemo(
    () =>
      markets.map((m) => ({
        kind: "market",
        id: m.id,
        label: m.title,
        description: m.question,
        href: `/markets/${m.slug}`,
        tag: CATEGORY_TAGS[m.status] ?? m.status
      })),
    [markets]
  );

  const communityResults: CommunityResult[] = useMemo(
    () =>
      communities.map((c) => ({
        kind: "community",
        id: c.id,
        label: c.name,
        description: c.description || "Community",
        href: `/communities/${c.slug}`,
        tag: "Community"
      })),
    [communities]
  );

  const filteredPages = useMemo(() => filterAndScore(PAGE_RESULTS, query), [query]);
  const filteredMarkets = useMemo(
    () => filterAndScore(marketResults, query).slice(0, 6),
    [marketResults, query]
  );
  const filteredCommunities = useMemo(
    () => filterAndScore(communityResults, query).slice(0, 4),
    [communityResults, query]
  );

  const groups = useMemo(() => {
    const g: { label: string; items: AnyResult[] }[] = [];
    if (filteredPages.length) g.push({ label: "Pages & Settings", items: filteredPages });
    if (filteredMarkets.length) g.push({ label: "Markets", items: filteredMarkets });
    if (filteredCommunities.length) g.push({ label: "Communities", items: filteredCommunities });
    return g;
  }, [filteredPages, filteredMarkets, filteredCommunities]);

  const flatResults = useMemo(() => groups.flatMap((g) => g.items), [groups]);

  const isEmpty = flatResults.length === 0;

  const navigateTo = (href: string) => {
    router.push(href);
    onClose();
  };

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, flatResults.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && flatResults[activeIndex]) {
        navigateTo(flatResults[activeIndex].href);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, flatResults, activeIndex, onClose]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  if (!isOpen) return null;

  let globalIndex = 0;

  return (
    <div className="search-overlay" onClick={onClose} aria-modal="true" role="dialog">
      <div className="search-modal" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-row">
          <svg className="search-input-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M10 10l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            ref={inputRef}
            className="search-input"
            placeholder="Search markets, communities, pages…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          {query && (
            <button className="search-clear-btn" onClick={() => setQuery("")} type="button">
              ✕
            </button>
          )}
        </div>

        <div className="search-results" ref={listRef}>
          {isEmpty ? (
            <div className="search-empty">
              <p>No results for <strong>&quot;{query}&quot;</strong></p>
              <span>Try searching for a market title, community name, or page.</span>
            </div>
          ) : (
            groups.map((group) => (
              <div className="search-group" key={group.label}>
                <div className="search-group-label">{group.label}</div>
                {group.items.map((result) => {
                  const index = globalIndex++;
                  const isActive = index === activeIndex;
                  return (
                    <Link
                      className={`search-item ${isActive ? "is-active" : ""}`}
                      href={result.href}
                      key={result.id}
                      onClick={onClose}
                      onMouseEnter={() => setActiveIndex(index)}
                    >
                      <span className="search-item-icon" aria-hidden="true">
                        {result.kind === "market" ? "📈" : result.kind === "community" ? "🏘" : "⚡"}
                      </span>
                      <span className="search-item-main">
                        <span className="search-item-title">{result.label}</span>
                        <span className="search-item-sub">{result.description}</span>
                      </span>
                      <span className="search-item-tag">{result.tag}</span>
                    </Link>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className="search-footer">
          <span><kbd>↑↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
};
