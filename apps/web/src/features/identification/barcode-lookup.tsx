"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { components } from "@/lib/api/schema";
import { barcodeApi, BarcodeFailure } from "./api";
import { BarcodeCandidates } from "./barcode-candidates";

export function BarcodeLookup({ apiOrigin }: { apiOrigin: string | null }) {
  const router = useRouter();
  const [gtin, setGtin] = useState("");
  const [result, setResult] = useState<components["schemas"]["BarcodeLookup"] | null>(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retryUntil, setRetryUntil] = useState(0);
  const [remaining, setRemaining] = useState(0);
  const request = useRef<AbortController | null>(null);
  const feedback = useRef<HTMLDivElement>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (result || error) feedback.current?.focus();
  }, [result, error]);
  useEffect(() => {
    if (!retryUntil) return;
    const timer = setInterval(() => {
      const seconds = Math.max(0, Math.ceil((retryUntil - Date.now()) / 1000));
      setRemaining(seconds);
      if (!seconds) clearInterval(timer);
    }, 250);
    return () => clearInterval(timer);
  }, [retryUntil]);

  async function submit(confirm: boolean) {
    if (request.current || !apiOrigin || Date.now() < retryUntil) return;
    const wine = result?.candidates
      .flatMap((candidate) => candidate.releases)
      .find((wine) => wine.id === selected);
    if (confirm && (!wine || !result)) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError("");
    if (!confirm) {
      setResult(null);
      setSelected("");
    }
    try {
      const api = barcodeApi(apiOrigin);
      if (confirm && wine && result) {
        const details = await api.confirm(
          {
            gtin: result.gtin,
            catalogReleaseId: wine.id,
            vintageStatus: wine.vintageStatus,
            year: wine.year,
            edition: wine.edition,
          },
          controller.signal,
        );
        if (!controller.signal.aborted) router.push(`/browse/${encodeURIComponent(details.id)}`);
      } else {
        const lookup = await api.lookup(gtin.trim(), controller.signal);
        if (!controller.signal.aborted) setResult(lookup);
      }
    } catch (failure) {
      if (controller.signal.aborted) return;
      const problem = failure instanceof BarcodeFailure ? failure : new BarcodeFailure(503);
      setError(problem.message);
      if (problem.status === 409) {
        setResult(null);
        setSelected("");
      }
      setRetryUntil(Date.now() + problem.retryAfter * 1000);
      setRemaining(problem.retryAfter);
    } finally {
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <details
      className="barcode-lookup"
      onToggle={(event) => {
        if (!event.currentTarget.open) {
          request.current?.abort();
          request.current = null;
          setBusy(false);
        }
      }}
    >
      <summary>Look up a barcode</summary>
      <p className="catalog-caption">
        Enter the numbers beneath the bottle’s barcode. Our barcode library is small and still
        growing.
      </p>
      {!apiOrigin ? (
        <p role="status">
          Barcode lookup is unavailable. You can search by name or add a wine manually.
        </p>
      ) : (
        <>
          <form
            className="catalog-search"
            onSubmit={(event) => {
              event.preventDefault();
              void submit(false);
            }}
          >
            <div>
              <label htmlFor="barcode-number">Barcode number</label>
              <input
                id="barcode-number"
                inputMode="numeric"
                autoComplete="off"
                type="text"
                required
                maxLength={14}
                pattern="(?:[0-9]{8}|[0-9]{12,14})"
                aria-describedby="barcode-help"
                value={gtin}
                disabled={busy}
                onChange={(event) => {
                  setGtin(event.target.value);
                  setResult(null);
                  setSelected("");
                  setError("");
                }}
              />
            </div>
            <button className="button" type="submit" disabled={busy || remaining > 0}>
              Look up bottle
            </button>
          </form>
          <p className="catalog-caption" id="barcode-help">
            Use 8, 12, 13 or 14 digits, including leading zeros.
          </p>
          <p role="status" aria-live="polite">
            {busy
              ? "Checking the bottle…"
              : remaining > 0
                ? `Try again in ${remaining} seconds.`
                : ""}
          </p>
          <div ref={feedback} tabIndex={-1} className="barcode-feedback">
            {error && <p role="alert">{error}</p>}
            {result?.status === "NOT_FOUND" && (
              <p>No match in our barcode library yet. Try the wine or producer name below.</p>
            )}
            {result?.status === "TOO_MANY_MATCHES" && (
              <p>This barcode has too many possible matches. Search by name to narrow it down.</p>
            )}
            {result?.status === "NEEDS_CONFIRMATION" && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void submit(true);
                }}
              >
                <h2>Check your bottle</h2>
                <p>
                  The same barcode can appear on different vintages. Match the wine, year and
                  edition to your label before continuing.
                </p>
                <fieldset disabled={busy || remaining > 0}>
                  <BarcodeCandidates
                    candidates={result.candidates}
                    selected={selected}
                    onSelect={setSelected}
                  />
                  <button className="button" type="submit" disabled={!selected}>
                    Confirm bottle &amp; view details
                  </button>
                </fieldset>
                <p className="catalog-caption">
                  Your vintage isn’t listed, or you’re unsure? Search by name or add it manually.
                  Don’t choose a different year.
                </p>
              </form>
            )}
          </div>
        </>
      )}
      <div className="capture-actions">
        <a
          className="text-link"
          href="#catalog-query"
          onClick={() => document.getElementById("catalog-query")?.focus()}
        >
          Search by name
        </a>
        <Link className="text-link" href="/capture">
          Add your bottle manually
        </Link>
      </div>
      <p className="catalog-caption">Looking up a bottle doesn’t add it to your journal.</p>
    </details>
  );
}
