import Link from "next/link";

const links = [
  { href: "/auth/sign-in", label: "Sign in" },
  { href: "/auth/sign-up", label: "Sign up" },
  { href: "/auth/passwordless", label: "Passwordless" },
  { href: "/auth/phone/verify", label: "Phone verify" },
  { href: "/auth/account", label: "Account" }
];

export const AuthRouteNav = () => {
  return (
    <nav className="auth-route-nav" aria-label="Authentication routes">
      {links.map((link) => (
        <Link className="auth-route-link" href={link.href} key={link.href}>
          {link.label}
        </Link>
      ))}
    </nav>
  );
};
