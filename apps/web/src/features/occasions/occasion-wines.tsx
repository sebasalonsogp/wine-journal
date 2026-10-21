"use client";

import { BottleCover } from "@/features/media/bottle-cover";

import Link from "next/link";
import { useRef, useState } from "react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { JournalError, releaseLabel } from "@/features/my-wines/wine-display";
import { RequestFailure } from "@/lib/session/http";
import { occasionKey, newOccasionDraft, storeOccasionDraft, type Occasion } from "./occasion-draft";
import { newComposer, readComposer, wineBodies, type Composer } from "./occasion-composer";
import { StagedWines } from "./staged-wines";

export function OccasionWines({ occasion }: { occasion: Occasion }) {
  const api = useJournalApi();
  const account = useAccount()!;
  const query = useInfiniteQuery({
    queryKey: ["occasion-wines", account.id, occasion.id],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      api.call((client, signal) =>
        client.GET("/api/v1/occasions/{occasion_id}/wines", {
          params: { path: { occasion_id: occasion.id }, query: { cursor: pageParam, limit: 20 } },
          signal,
        }),
      ),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
  });
  const wines = query.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <section className="occasion-wines" aria-labelledby="occasion-wines-title">
      <h2 id="occasion-wines-title">Wines we tried</h2>
      {query.isPending ? (
        <p role="status">Opening wines…</p>
      ) : query.error ? (
        <JournalError error={query.error} retry={() => void query.refetch()} />
      ) : wines.length ? (
        <ul className="occasion-wine-list">
          {wines.map((wine) => (
            <li key={wine.id}>
              <Link className="occasion-wine-card" href={`/my-wines/${wine.id}`} prefetch={false}>
                <BottleCover api={api} assetId={wine.coverAssetId} name={wine.name} />
                <div>
                  <h3>{wine.name}</h3>
                  <p>{releaseLabel(wine)}</p>
                  <p>
                    {wine.entryCount} drinking {wine.entryCount === 1 ? "entry" : "entries"} at this
                    occasion
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p>No wines added yet.</p>
      )}
      {query.hasNextPage && (
        <button
          type="button"
          className="text-button"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          Load more wines
        </button>
      )}
      <AddOccasionWines occasion={occasion} />
      <p className="form-footnote">
        Already logged it? <Link href="/my-wines">Open My wines</Link> and choose Organize occasion
        on the drinking entry.
      </p>
    </section>
  );
}

function AddOccasionWines({ occasion }: { occasion: Occasion }) {
  const account = useAccount()!;
  const api = useJournalApi();
  const queries = useQueryClient();
  const key = `${occasionKey(account.id, occasion.id)}:add-wines`;
  const [draft, setDraft] = useState<Composer | null>(() => readComposer(key));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const submitting = useRef(false);
  function change(next: Composer) {
    setDraft(next);
    const saved = storeOccasionDraft(key, next);
    if (!saved) setNotice("Draft storage is unavailable. Keep this page open.");
    return saved;
  }
  async function save() {
    if (!draft || draft.child || !draft.wines.length || submitting.current) return;
    const next = { ...draft, attempted: true };
    if (!change(next)) {
      setDraft({ ...next, attempted: false });
      setError("Enable session storage before saving so retries stay safe.");
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      await api.call((client, signal) =>
        client.POST("/api/v1/occasions/{occasion_id}/wines", {
          params: {
            path: { occasion_id: occasion.id },
            header: { "idempotency-key": next.intentKey },
          },
          body: { wines: wineBodies(next.wines) },
          signal,
        }),
      );
      storeOccasionDraft(key, null);
      setDraft(null);
      await Promise.all(
        ["occasion-wines", "wines", "wine", "entries"].map((name) =>
          queries.invalidateQueries({ queryKey: [name, account.id] }),
        ),
      );
      setNotice("Wines added to your occasion.");
    } catch (failure) {
      if (failure instanceof RequestFailure && [404, 422].includes(failure.status))
        change({ ...next, attempted: false });
      setError(
        failure instanceof Error
          ? failure.message
          : "We couldn’t confirm the save. Retry with the same wines.",
      );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  return draft ? (
    <form
      className="occasion-editor"
      aria-label="Add wines to occasion"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      {draft.attempted && (
        <p role="status">This save may already be recorded. Retry with the same wines to check.</p>
      )}
      <StagedWines draft={draft} change={change} disabled={busy || draft.attempted} />
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <div className="capture-actions">
        <button
          type="submit"
          className="button"
          disabled={busy || Boolean(draft.child) || !draft.wines.length}
        >
          {busy ? "Saving…" : draft.attempted ? "Retry wine save" : "Save wines"}
        </button>
        {!draft.attempted && (
          <button
            type="button"
            className="text-button"
            onClick={() => {
              if (window.confirm("Discard these unsaved wines?")) {
                storeOccasionDraft(key, null);
                setDraft(null);
                setError("");
                setNotice("");
              }
            }}
          >
            Discard wine draft
          </button>
        )}
      </div>
    </form>
  ) : (
    <>
      <button
        type="button"
        className="button button-secondary"
        onClick={() => {
          setNotice("");
          change(newComposer({ ...newOccasionDraft(occasion), version: null }));
        }}
      >
        Add wines to occasion
      </button>
      {notice && <p role="status">{notice}</p>}
    </>
  );
}
