import Link from "next/link";

const links = [
  { href: "/communities", label: "Communities" },
  { href: "/market-requests", label: "Market requests" },
  { href: "/markets", label: "Markets" },
  { href: "/admin/review", label: "Admin review" },
  { href: "/auth/account", label: "Account" }
];

export const AppRouteNav = () => {
  return (
    <nav className="auth-route-nav" aria-label="Application routes">
      {links.map((link) => (
        <Link className="auth-route-link" href={link.href} key={link.href}>
          {link.label}
        </Link>
      ))}
    </nav>
  );
};
