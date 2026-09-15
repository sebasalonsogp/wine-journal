"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { authRequest } from "@/lib/session/http";
import type { AuthProvider } from "./validation";

const labels = { google: "Google", apple: "Apple", facebook: "Facebook" };

export function SignInForm({
  next,
  providers,
  initialError,
}: {
  next: string;
  providers: AuthProvider[];
  initialError: string;
}) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [stage, setStage] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const [notice, setNotice] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const codeInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (stage === "code") codeInput.current?.focus();
  }, [stage]);
  useEffect(() => {
    if (!cooldown) return;
    const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  async function act(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  async function sendCode() {
    await authRequest("/auth/otp/request", { email });
    setStage("code");
    setCooldown(60);
    setNotice("A new code is on its way. Check your inbox and spam folder.");
  }
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void act(async () => {
      if (stage === "email") {
        await sendCode();
        return;
      }
      const result = await authRequest<{ next: string }>("/auth/otp/verify", { email, code, next });
      const channel = new BroadcastChannel("wine-journal-auth");
      channel.postMessage("account-changed");
      channel.close();
      window.location.replace(result.next);
    });
  }

  return (
    <section className="sign-in-panel" aria-labelledby="sign-in-title">
      <h1 id="sign-in-title">
        {stage === "email" ? "A journal of your own." : "Check your inbox."}
      </h1>
      <p className="form-intro">
        {stage === "email" ? (
          "Sign in or create an account with an email code. Your wines and memories stay private."
        ) : (
          <>
            We sent a six-digit code to <strong className="email-address">{email}</strong>. It
            expires in 10 minutes.
          </>
        )}
      </p>
      {providers.length > 0 && stage === "email" && (
        <div className="social-options">
          {providers.map((provider) => (
            <button
              className="button button-secondary"
              key={provider}
              disabled={busy}
              onClick={() =>
                void act(async () => {
                  const result = await authRequest<{ url: string }>("/auth/oauth", {
                    provider,
                    next,
                  });
                  window.location.assign(result.url);
                })
              }
            >
              Continue with {labels[provider]}
            </button>
          ))}
          <p className="divider-label">or use your email</p>
        </div>
      )}
      <form onSubmit={submit} aria-busy={busy}>
        {stage === "email" ? (
          <div className="form-field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              maxLength={254}
              required
              disabled={busy}
              aria-describedby={error ? "auth-error" : undefined}
            />
          </div>
        ) : (
          <div className="form-field">
            <label htmlFor="code">Verification code</label>
            <input
              ref={codeInput}
              id="code"
              className="code-input"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
              required
              disabled={busy}
              aria-describedby={error ? "auth-error" : undefined}
            />
          </div>
        )}
        {error && (
          <p className="form-message" role="alert" id="auth-error">
            {error}
          </p>
        )}
        {notice && (
          <p className="form-message text-secondary" role="status">
            {notice}
          </p>
        )}
        <button className="button form-submit" disabled={busy} type="submit">
          {busy ? "Please wait…" : stage === "email" ? "Send me a code" : "Open my journal"}
        </button>
      </form>
      {stage === "code" ? (
        <div className="recovery-actions">
          <button
            className="text-button"
            disabled={busy || cooldown > 0}
            onClick={() => void act(sendCode)}
          >
            {cooldown > 0 ? `Resend code in ${cooldown}s` : "Send a new code"}
          </button>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => {
              setStage("email");
              setCode("");
              setError("");
              setNotice("");
            }}
          >
            Use a different email
          </button>
        </div>
      ) : (
        <p className="form-footnote">
          No password to remember. Use the same email each time you return.
        </p>
      )}
      <Link className="back-link" href="/browse">
        Continue browsing
      </Link>
    </section>
  );
}
