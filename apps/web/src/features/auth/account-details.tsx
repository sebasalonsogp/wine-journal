"use client";
import { useAccount } from "./journal-shell";

export function AccountDetails() {
  const account = useAccount();
  if (!account) return null;
  return (
    <section className="account-details">
      <h2>Your private journal</h2>
      <p>Use your sign-in method to return to this account.</p>
      <dl>
        <dt>Signed in as</dt>
        <dd data-testid="account-email">{account.email ?? "Your connected account"}</dd>
        <dt>Privacy</dt>
        <dd>Your journal is private.</dd>
      </dl>
      <p className="availability-note">Taste preferences and profile editing are coming later.</p>
    </section>
  );
}
