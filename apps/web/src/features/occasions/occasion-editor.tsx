"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { RequestFailure } from "@/lib/session/http";
import { dateLabel } from "@/features/my-wines/wine-display";
import {
  newOccasionDraft,
  occasionBody,
  occasionKey,
  storeOccasionDraft,
  type Occasion,
} from "./occasion-draft";
import { OccasionFields } from "./occasion-fields";
import { newComposer, readComposer, composerBody, type Composer } from "./occasion-composer";
import { StagedWines } from "./staged-wines";

export function OccasionEditor({ occasion }: { occasion?: Occasion }) {
  const account = useAccount()!;
  const api = useJournalApi();
  const router = useRouter();
  const queries = useQueryClient();
  const key = occasionKey(account.id, occasion?.id);
  const [draft, setDraft] = useState<Composer | null>(
    () => readComposer(key) ?? (occasion ? null : newComposer()),
  );
  const [latest, setLatest] = useState<Occasion | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const submitting = useRef(false);

  async function refresh() {
    await Promise.all([
      queries.invalidateQueries({ queryKey: ["occasions", account.id] }),
      queries.invalidateQueries({ queryKey: ["occasion", account.id, occasion?.id] }),
      queries.invalidateQueries({ queryKey: ["wines", account.id] }),
      queries.invalidateQueries({ queryKey: ["wine", account.id] }),
      queries.invalidateQueries({ queryKey: ["entries", account.id] }),
    ]);
  }

  function change(next: Composer) {
    setDraft(next);
    const stored = storeOccasionDraft(key, next);
    if (!stored)
      setNotice("Draft storage is unavailable. Keep this page open until your changes are saved.");
    return stored;
  }

  async function save(version: number | null) {
    if (!draft || draft.child || submitting.current) return;
    const next = { ...draft, version, attempted: true };
    if (!change(next) && !occasion) {
      setDraft({ ...next, attempted: false });
      setError("Your browser couldn’t keep the save key. Enable session storage, then try again.");
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const body = occasionBody(next);
      const saved = occasion
        ? await api.call((client, signal) =>
            client.PUT("/api/v1/occasions/{occasion_id}", {
              params: { path: { occasion_id: occasion.id } },
              body: { ...body, version: version! },
              signal,
            }),
          )
        : await api.call((client, signal) =>
            client.POST("/api/v1/occasions", {
              params: { header: { "idempotency-key": next.intentKey } },
              body: composerBody(next),
              signal,
            }),
          );
      storeOccasionDraft(key, null);
      setDraft(null);
      setLatest(null);
      await refresh();
      router.push(`/occasions/${saved.id}`);
    } catch (failure) {
      if (occasion && failure instanceof RequestFailure && failure.status === 409) {
        try {
          setLatest(
            await api.call((client, signal) =>
              client.GET("/api/v1/occasions/{occasion_id}", {
                params: { path: { occasion_id: occasion.id } },
                signal,
              }),
            ),
          );
        } catch {
          setError(
            "We couldn’t load the latest occasion. Your draft is kept; try saving again to review it.",
          );
        }
      } else if (failure instanceof RequestFailure && failure.status === 422) {
        change({ ...next, attempted: false });
        setError("Check the occasion and wine details, then save again. Your draft is kept.");
      } else {
        setError(
          failure instanceof RequestFailure && [401, 403, 404].includes(failure.status)
            ? failure.message
            : "We couldn’t confirm the save. Your draft is kept; retry to check without creating another occasion.",
        );
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  if (!draft && !occasion) return <p role="status">Opening your occasion…</p>;
  if (!draft)
    return (
      <button
        className="button button-secondary"
        onClick={() => change(newComposer(newOccasionDraft(occasion)))}
      >
        Edit occasion
      </button>
    );
  const locked = !occasion && draft.attempted;
  return (
    <form
      className="occasion-editor"
      aria-label={occasion ? "Edit occasion" : "New occasion"}
      aria-busy={busy}
      onSubmit={(event) => {
        event.preventDefault();
        if (!latest) void save(draft.version);
      }}
    >
      {locked && (
        <p className="save-notice">
          This save may already have reached your journal. Retry with these same details to check.
        </p>
      )}
      <OccasionFields
        draft={draft}
        disabled={busy || locked}
        change={(fields) => change({ ...draft, ...fields })}
      />
      {!occasion && <StagedWines draft={draft} disabled={busy || locked} change={change} />}
      {latest && (
        <section className="edit-conflict" aria-labelledby={`occasion-conflict-${latest.id}`}>
          <h3 id={`occasion-conflict-${latest.id}`}>This occasion has changed</h3>
          <p role="alert">
            Your draft is kept above. Review the latest saved details before choosing what to keep.
          </p>
          <dl>
            <dt>Title</dt>
            <dd>{latest.title || dateLabel(latest.occasionDate)}</dd>
            <dt>Date and time</dt>
            <dd>
              {dateLabel(latest.occasionDate)}
              {latest.localTime
                ? ` · ${latest.localTime.slice(0, 5)} · ${latest.timezone}`
                : " · Time not recorded"}
            </dd>
            <dt>Location</dt>
            <dd>{latest.locationLabel || "Not recorded"}</dd>
            <dt>Notes</dt>
            <dd className="entry-notes">{latest.notes || "No notes"}</dd>
          </dl>
          <div className="capture-actions">
            <button
              type="button"
              className="button"
              disabled={busy}
              onClick={(event) => {
                if (event.currentTarget.form?.reportValidity()) void save(latest.version);
              }}
            >
              Save my changes over this version
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => {
                storeOccasionDraft(key, null);
                setDraft(null);
                setLatest(null);
                setError("");
                void refresh();
              }}
            >
              Use latest saved occasion
            </button>
          </div>
        </section>
      )}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <div className="capture-actions">
        {!latest && (
          <button type="submit" className="button" disabled={busy || Boolean(draft.child)}>
            {busy
              ? "Saving…"
              : locked
                ? "Retry save"
                : occasion
                  ? "Save changes"
                  : "Create occasion"}
          </button>
        )}
        {!locked && (
          <button
            type="button"
            className="text-button"
            disabled={busy}
            onClick={() => {
              if (window.confirm("Discard your unsaved occasion details?")) {
                storeOccasionDraft(key, null);
                if (occasion) {
                  setDraft(null);
                  setLatest(null);
                  setError("");
                  setNotice("");
                } else router.push("/occasions");
              }
            }}
          >
            Discard changes
          </button>
        )}
      </div>
    </form>
  );
}
