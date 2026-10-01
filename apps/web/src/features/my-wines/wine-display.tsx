import Link from "next/link";
import type { components } from "@/lib/api/schema";
import { RequestFailure } from "@/lib/session/http";

export type Wine = components["schemas"]["WineResponse"];
export function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value + "T00:00:00Z"));
}
export function releaseLabel(wine: Wine) {
  const vintage =
    wine.vintageStatus === "YEAR"
      ? String(wine.year)
      : ({ NON_VINTAGE: "Non-vintage", MULTI_VINTAGE: "Multi-vintage", UNKNOWN: "Vintage unknown" }[
          wine.vintageStatus
        ] ?? "Vintage unknown");
  return [vintage, wine.edition].filter(Boolean).join(" · ");
}
export function BottlePlaceholder() {
  return (
    <div className="bottle-placeholder" aria-label="No bottle image yet" role="img">
      <svg width="40" height="100" viewBox="0 0 40 100" fill="none" aria-hidden="true">
        <path
          d="M15 5h10v23c0 6 9 9 9 18v44c0 4-2 5-5 5H11c-3 0-5-1-5-5V46c0-9 9-12 9-18V5Z"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path d="M15 14h10M7 53h26v25H7" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    </div>
  );
}
export function JournalError({ error, retry }: { error: Error; retry: () => void }) {
  return (
    <div className="journal-error">
      <p role="alert">{error.message}</p>
      {error instanceof RequestFailure && error.status === 401 ? (
        <Link className="button" href="/auth/sign-in">
          Sign in again
        </Link>
      ) : (
        <button className="button button-secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
