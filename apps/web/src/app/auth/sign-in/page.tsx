import Link from "next/link";
import { WineMark } from "@/components/app-header";
import { SignInForm } from "@/features/auth/sign-in-form";
import { authConfig } from "@/features/auth/config";
import { returnPath } from "@/features/auth/validation";

export const dynamic = "force-dynamic";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const error =
    params.error === "session"
      ? "Please sign in to continue to your journal."
      : params.error === "callback"
        ? "Sign-in wasn't completed. Try again or use an email code."
        : "";
  let config;
  try {
    config = authConfig();
  } catch {
    /* Render a recoverable state without exposing configuration. */
  }
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="sign-in-header">
        <Link className="brand" href="/browse">
          <span className="brand-mark">
            <WineMark />
          </span>
          Wine Journal
        </Link>
      </header>
      <main id="main" className="sign-in-layout">
        <div className="sign-in-story">
          <h2>
            Remember the wine.
            <br />
            Keep the moment.
          </h2>
          <p>
            The bottle at dinner. A first taste of somewhere new. A small discovery worth coming
            back to.
          </p>
          <p className="story-note">Your taste, one wine at a time.</p>
        </div>
        {config ? (
          <SignInForm
            next={returnPath(params.next)}
            providers={config.providers}
            initialError={error}
          />
        ) : (
          <section className="sign-in-panel">
            <h1>Sign-in is taking a moment.</h1>
            <p>Please try again shortly.</p>
            <Link href="/browse" className="back-link">
              Continue browsing
            </Link>
          </section>
        )}
      </main>
    </>
  );
}
