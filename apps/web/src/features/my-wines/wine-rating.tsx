"use client";

import { useId, useRef, useState } from "react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import type { components } from "@/lib/api/schema";
import { RequestFailure } from "@/lib/session/http";
import { JournalError } from "./wine-display";
import { ratingKey, readRatingDraft, storeRatingDraft, type RatingDraft } from "./rating-draft";

type Wine = components["schemas"]["WineResponse"];
const scores = Array.from({ length: 9 }, (_, index) => 1 + index / 2);
const scoreLabel = (score: number | null) => (score === null ? "Not rated yet" : `${score} / 5`);

export function WineRating({ wine }: { wine: Wine }) {
  const api = useJournalApi();
  const account = useAccount()!;
  const queries = useQueryClient();
  const id = useId();
  const key = ratingKey(account.id, wine.id);
  const [draft, setDraft] = useState<RatingDraft | null>(() => readRatingDraft(key));
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [storageWarning, setStorageWarning] = useState(false);
  const submitting = useRef(false);
  const conflict = draft !== null && draft.version !== wine.ratingVersion;
  const selection = draft?.score === undefined ? wine.currentRating : draft.score;
  const history = useInfiniteQuery({
    queryKey: ["ratings", account.id, wine.id],
    enabled: expanded,
    initialPageParam: undefined as number | undefined,
    queryFn: ({ pageParam }) =>
      api.call((client, signal) =>
        client.GET("/api/v1/me/wines/{wine_id}/rating-history", {
          params: { path: { wine_id: wine.id }, query: { limit: 20, beforeVersion: pageParam } },
          signal,
        }),
      ),
    getNextPageParam: (page) => page.nextBeforeVersion ?? undefined,
  });

  function remember(value: RatingDraft | null) {
    setDraft(value);
    setStorageWarning(!storeRatingDraft(key, value));
  }

  async function refresh() {
    await Promise.all([
      queries.invalidateQueries({ queryKey: ["wine", account.id, wine.id] }),
      queries.invalidateQueries({ queryKey: ["wines", account.id] }),
      queries.invalidateQueries({ queryKey: ["ratings", account.id, wine.id] }),
    ]);
  }

  async function save(score: number | null, erase = false) {
    if (submitting.current) return;
    const version = erase ? wine.ratingVersion : (draft?.version ?? wine.ratingVersion);
    if (
      erase &&
      !window.confirm(
        `Delete all rating history for ${wine.name}? This permanently removes your past ratings and clears your current rating. Your wine and drinking entries will stay.`,
      )
    )
      return;
    submitting.current = true;
    setBusy(true);
    setMessage("");
    setError("");
    if (!erase) remember({ score, version });
    try {
      if (erase) {
        await api.call((client, signal) =>
          client.DELETE("/api/v1/me/wines/{wine_id}/rating-history", {
            params: { path: { wine_id: wine.id }, query: { version } },
            signal,
          }),
        );
      } else {
        await api.call((client, signal) =>
          client.PUT("/api/v1/me/wines/{wine_id}/rating", {
            params: { path: { wine_id: wine.id } },
            body: { score, version },
            signal,
          }),
        );
      }
      remember(null);
      setMessage(
        erase
          ? "Rating history deleted."
          : score === null
            ? "Rating cleared. Your history is still here."
            : "Rating saved.",
      );
    } catch (failure) {
      setError(
        failure instanceof RequestFailure && failure.status === 409
          ? "Your rating changed or another save is in progress. Review the current rating before trying again."
          : failure instanceof RequestFailure && [401, 403, 404].includes(failure.status)
            ? failure.message
            : "We couldn’t confirm the change. Check the current rating and history before trying again.",
      );
    } finally {
      await refresh();
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <section className="wine-rating" aria-labelledby={`${id}-title`}>
      <div className="rating-heading">
        <h2 id={`${id}-title`}>My rating</h2>
        <p className="rating-current" data-testid="current-rating">
          {scoreLabel(wine.currentRating)}
        </p>
      </div>
      <p className="rating-intro">Your opinion of this wine, with room to change your mind.</p>
      <form
        className="rating-form"
        onSubmit={(event) => {
          event.preventDefault();
          void save(selection);
        }}
      >
        <div className="rating-field">
          <label htmlFor={`${id}-score`}>Your score</label>
          <select
            id={`${id}-score`}
            value={selection ?? ""}
            disabled={busy}
            onChange={(event) => {
              remember({
                score: event.target.value === "" ? null : Number(event.target.value),
                version: draft?.version ?? wine.ratingVersion,
              });
              setMessage("");
            }}
          >
            <option value="">Unrated</option>
            {scores.map((score) => (
              <option key={score} value={score}>
                {score} / 5
              </option>
            ))}
          </select>
        </div>
        <button className="button" disabled={busy || conflict || selection === wine.currentRating}>
          {busy ? "Saving…" : "Save rating"}
        </button>
        {wine.currentRating !== null && (
          <button
            type="button"
            className="text-button"
            disabled={busy || conflict}
            onClick={() => void save(null)}
          >
            Clear rating
          </button>
        )}
      </form>
      {storageWarning && (
        <p role="status">This browser cannot keep your unsaved choice when you leave the page.</p>
      )}
      {conflict && (
        <div className="rating-conflict" role="alert">
          <p>
            The current rating is {scoreLabel(wine.currentRating)}. Your unsaved choice is{" "}
            {selection === null ? "Unrated" : scoreLabel(selection)}.
          </p>
          <div className="capture-actions">
            <button
              type="button"
              className="button button-secondary"
              disabled={busy}
              onClick={() => {
                remember({ score: selection, version: wine.ratingVersion });
                setError("");
              }}
            >
              Keep my choice to save
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => {
                remember(null);
                setError("");
              }}
            >
              Discard my choice
            </button>
          </div>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      <button
        type="button"
        className="text-button rating-history-toggle"
        aria-expanded={expanded}
        aria-controls={`${id}-history`}
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "Hide rating history" : "View rating history"}
      </button>
      {expanded && (
        <div id={`${id}-history`} className="rating-history">
          {history.isPending ? (
            <p role="status">Opening rating history…</p>
          ) : history.error ? (
            <JournalError error={history.error} retry={() => void history.refetch()} />
          ) : (
            <>
              <p>Each change is dated. Your current rating is your latest choice.</p>
              {history.data?.pages[0].items.length === 0 ? (
                <p>No rating history yet.</p>
              ) : (
                <>
                  <ol className="rating-revisions">
                    {history.data?.pages
                      .flatMap((page) => page.items)
                      .map((item) => (
                        <li key={item.version}>
                          <span>
                            {item.score === null ? "Rating cleared" : scoreLabel(item.score)}
                          </span>
                          <time dateTime={item.changedAt}>
                            {new Intl.DateTimeFormat(undefined, {
                              dateStyle: "medium",
                              timeStyle: "short",
                            }).format(new Date(item.changedAt))}
                          </time>
                        </li>
                      ))}
                  </ol>
                  {history.hasNextPage && (
                    <button
                      type="button"
                      className="button button-secondary"
                      disabled={history.isFetchingNextPage}
                      onClick={() => void history.fetchNextPage()}
                    >
                      {history.isFetchingNextPage ? "Loading…" : "Load older ratings"}
                    </button>
                  )}
                  <button
                    type="button"
                    className="text-button rating-erase"
                    disabled={busy}
                    onClick={() => void save(null, true)}
                  >
                    Delete rating history
                  </button>
                </>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
