"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  ["/browse", "Browse wines"],
  ["/my-wines", "My wines"],
  ["/occasions", "Occasions"],
  ["/guides", "Guides"],
];

export function WineMark() {
  return (
    <svg
      aria-hidden="true"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 3h6l1 6a4 4 0 0 1-8 0l1-6ZM12 13v7m-3 0h6M8 8h8" />
    </svg>
  );
}

export function AppHeader({
  signedIn = false,
  onSignOut,
  signingOut = false,
}: {
  signedIn?: boolean;
  onSignOut?: () => void;
  signingOut?: boolean;
}) {
  const path = usePathname();
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="app-header">
        <Link className="brand" href="/browse">
          <span className="brand-mark">
            <WineMark />
          </span>
          Wine Journal
        </Link>
        <nav aria-label="Main navigation" className="main-nav">
          {navigation.map(([href, title]) => (
            <Link
              key={href}
              href={href}
              prefetch={false}
              aria-current={path === href ? "page" : undefined}
            >
              {title}
            </Link>
          ))}
        </nav>
        <div className="account-nav">
          {signedIn ? (
            <>
              <Link
                href="/profile"
                prefetch={false}
                aria-current={path === "/profile" ? "page" : undefined}
              >
                My account
              </Link>
              <button className="text-button" onClick={onSignOut} disabled={signingOut}>
                {signingOut ? "Signing out…" : "Sign out"}
              </button>
            </>
          ) : (
            <Link className="button button-small" href="/auth/sign-in">
              Sign in
            </Link>
          )}
        </div>
      </header>
    </>
  );
}
