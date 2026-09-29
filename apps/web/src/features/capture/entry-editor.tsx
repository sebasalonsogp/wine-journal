"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { RequestFailure } from "@/lib/session/http";
import {
  editBody,
  editKey,
  entryDraft,
  readEditDraft,
  storeEditDraft,
  type EditDraft,
  type Entry,
} from "./edit-draft";
import { EntryFields } from "./entry-fields";
import { EntryDeletion } from "./entry-deletion";

export function EntryEditor({ entry, label }: { entry: Entry; label: string }) {
  const account = useAccount()!;
  const api = useJournalApi();
  const queries = useQueryClient();
  const key = editKey(account.id, entry.id);
  const [draft, setDraft] = useState<EditDraft | null>(() => readEditDraft(key));
  const [latest, setLatest] = useState<Entry | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const submitting = useRef(false);

  function change(next: EditDraft) {
    setDraft(next);
    if (!storeEditDraft(key, next))
      setNotice("Draft storage is unavailable. Save before leaving or switching tabs.");
  }

  async function refresh() {
    await Promise.all([
      queries.invalidateQueries({ queryKey: ["entries", account.id, entry.userWineId] }),
      queries.invalidateQueries({ queryKey: ["wine", account.id, entry.userWineId] }),
      queries.invalidateQueries({ queryKey: ["wines", account.id] }),
    ]);
  }

  async function save(version: number) {
    if (!draft || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    const next = { ...draft, version };
    change(next);
    try {
      await api.call((client, signal) =>
        client.PATCH("/api/v1/entries/{entry_id}", {
          params: { path: { entry_id: entry.id } },
          body: editBody(next),
          signal,
        }),
      );
      storeEditDraft(key, null);
      setDraft(null);
      setLatest(null);
      setNotice("Entry updated.");
      await refresh();
    } catch (failure) {
      if (failure instanceof RequestFailure && failure.status === 409) {
        try {
          setLatest(
            await api.call((client, signal) =>
              client.GET("/api/v1/entries/{entry_id}", {
                params: { path: { entry_id: entry.id } },
                signal,
              }),
            ),
          );
        } catch {
          setError(
            "We couldn’t load the latest entry. Your draft is kept; try saving again to review it.",
          );
        }
      } else {
        setError(
          failure instanceof RequestFailure && failure.status === 422
            ? "Check the date, local time and timezone. Your notes are kept."
            : failure instanceof RequestFailure && failure.status === 401
              ? "Your session has ended. Your draft is kept for this account; sign in again to continue."
              : "We couldn’t confirm the update. Your draft is kept; try saving again.",
        );
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  if (!draft)
    return (
      <div className="entry-controls">
        <button
          className="text-button"
          onClick={() => {
            setNotice("");
            change(entryDraft(entry));
          }}
        >
          Edit entry
        </button>
        <EntryDeletion entry={entry} label={label} />
        {notice && <p role="status">{notice}</p>}
      </div>
    );

  return (
    <form
      className="entry-editor"
      aria-label="Edit drinking entry"
      aria-busy={busy}
      onSubmit={(event) => {
        event.preventDefault();
        if (!latest) void save(draft.version);
      }}
    >
      <EntryFields draft={draft} busy={busy} change={change} />
      {latest && (
        <section className="edit-conflict" aria-labelledby={`conflict-${entry.id}`}>
          <h3 id={`conflict-${entry.id}`}>This entry has changed</h3>
          <p role="alert">
            Your draft above is kept. Review the latest saved entry before choosing what to keep.
          </p>
          <dl>
            <dt>Date and time</dt>
            <dd>
              {latest.consumedDate}
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
                if (event.currentTarget.form?.reportValidity()) void save(latest.version ?? 1);
              }}
            >
              Save my changes over this version
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => {
                storeEditDraft(key, null);
                setDraft(null);
                setLatest(null);
                setError("");
                void refresh();
              }}
            >
              Use latest saved entry
            </button>
          </div>
        </section>
      )}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <div className="capture-actions">
        {!latest && (
          <button className="button" type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save changes"}
          </button>
        )}
        <button
          className="text-button"
          type="button"
          disabled={busy}
          onClick={() => {
            if (window.confirm("Discard your unsaved changes to this entry?")) {
              storeEditDraft(key, null);
              setDraft(null);
              setLatest(null);
              setError("");
              setNotice("");
            }
          }}
        >
          Cancel editing
        </button>
      </div>
    </form>
  );
}
