"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { usePathname, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import {
  MARKET_DISCOVERY_CATEGORIES,
  isMarketDiscoveryCategory
} from "@/lib/markets/discovery";
import { NotificationBell } from "@/components/app/notification-bell";
import { SearchModal } from "@/components/app/search-modal";

const primaryLinks = [
  { href: "/markets", label: "Markets" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/wallet", label: "Wallet" },
  { href: "/communities", label: "Communities" },
  { href: "/about", label: "About" }
];

const menuLinks = [
  { href: "/communities", label: "Communities" },
  { href: "/markets", label: "Markets" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/creators", label: "Creator dashboard" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/market-requests", label: "Propose a market" },
  { href: "/ops", label: "Operations" },
  { href: "/about", label: "About Satta" }
];

const isActiveRoute = (pathname: string, href: string) => pathname === href || pathname.startsWith(`${href}/`);

export const AppRouteNav = () => {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { backendUser, signOut, user } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const openSearch = useCallback(() => setIsSearchOpen(true), []);
  const closeSearch = useCallback(() => setIsSearchOpen(false), []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  const userGlyph = user?.email?.charAt(0).toUpperCase() || "U";
  const accountLabel = user?.user_metadata?.display_name || user?.email || "Account";
  const isLandingPage = pathname === "/";
  const activeCategory = isMarketDiscoveryCategory(searchParams.get("category"))
    ? searchParams.get("category")
    : "Trending";

  return (
    <header className="topnav">
      <div className="topnav-inner">
        <Link href="/" className="topnav-brand">
          <span className="topnav-brand-dot" aria-hidden="true" />
          Satta
        </Link>

        <nav className="topnav-links" aria-label="Application routes">
          {primaryLinks.map((link) => (
            <Link
              className={`topnav-link ${isActiveRoute(pathname, link.href) ? "is-active" : ""}`}
              href={link.href}
              key={link.href}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="topnav-end">
          <button className="topnav-search-btn" onClick={openSearch} type="button" aria-label="Search">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
              <path d="M10 10l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span className="topnav-search-label">Search</span>
            <kbd className="topnav-search-kbd">⌘K</kbd>
          </button>

          <Link
            className={`topnav-create-btn ${isActiveRoute(pathname, "/market-requests") ? "is-active" : ""}`}
            href="/market-requests"
          >
            + Create Market
          </Link>

          <NotificationBell />

          <div className="topnav-account-menu" ref={menuRef}>
            <button
              aria-expanded={isMenuOpen}
              aria-haspopup="menu"
              className={`topnav-account-btn ${isActiveRoute(pathname, "/auth/account") ? "is-active" : ""}`}
              onClick={() => setIsMenuOpen((current) => !current)}
              type="button"
            >
              <span className="topnav-account-avatar" aria-hidden="true">
                {userGlyph}
              </span>
              <span className="topnav-account-copy">{user ? "My account" : "Sign in"}</span>
            </button>
            {isMenuOpen ? (
              <div className="topnav-account-dropdown" role="menu">
                <div className="topnav-account-summary">
                  <span className="topnav-account-summary-label">Signed {user ? "in" : "out"}</span>
                  <strong>{accountLabel}</strong>
                </div>
                <div className="topnav-account-group">
                  {menuLinks.map((link) => (
                    <Link
                      className={`topnav-account-item ${isActiveRoute(pathname, link.href) ? "is-active" : ""}`}
                      href={link.href}
                      key={link.href}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
                {backendUser?.is_admin ? (
                  <div className="topnav-account-group">
                    <Link
                      className={`topnav-account-item ${isActiveRoute(pathname, "/admin/review") ? "is-active" : ""}`}
                      href="/admin/review"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Admin review
                    </Link>
                  </div>
                ) : null}
                {user ? (
                  <div className="topnav-account-group">
                    <Link className="topnav-account-item" href="/auth/account" onClick={() => setIsMenuOpen(false)}>
                      Account settings
                    </Link>
                    <button
                      className="topnav-account-item topnav-account-item-danger"
                      onClick={async () => {
                        await signOut();
                        setIsMenuOpen(false);
                        router.push("/auth/sign-in");
                      }}
                      type="button"
                    >
                      Sign out
                    </button>
                  </div>
                ) : (
                  <div className="topnav-account-group">
                    <Link className="topnav-account-item" href="/auth/sign-in" onClick={() => setIsMenuOpen(false)}>
                      Sign in
                    </Link>
                    <Link className="topnav-account-item" href="/auth/sign-up" onClick={() => setIsMenuOpen(false)}>
                      Create account
                    </Link>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <SearchModal isOpen={isSearchOpen} onClose={closeSearch} />

      {isLandingPage ? (
        <div className="topnav-discovery-shell">
          <div className="topnav-discovery">
            <span className="topnav-discovery-label">Browse by category</span>
            <nav className="topnav-discovery-links" aria-label="Landing market categories">
              {MARKET_DISCOVERY_CATEGORIES.map((category) => (
                <Link
                  className={`topnav-discovery-link ${activeCategory === category ? "is-active" : ""}`}
                  href={category === "Trending" ? "/" : `/?category=${encodeURIComponent(category)}`}
                  key={category}
                >
                  {category}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      ) : null}
    </header>
  );
};
