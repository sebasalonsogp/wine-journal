"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { RequestFailure } from "@/lib/session/http";
import { editKey, storeEditDraft, type Entry } from "./edit-draft";

export function EntryDeletion({ entry, label }: { entry: Entry; label: string }) {
  const api = useJournalApi();
  const account = useAccount()!;
  const queries = useQueryClient();
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const submitting = useRef(false);
  const [selected, setSelected] = useState<{ entry: Entry; label: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!selected) return;
    const element = dialog.current!;
    element.showModal();
    cancel.current?.focus();
    return () => element.close();
  }, [selected]);

  function closeDialog() {
    dialog.current?.close();
    setSelected(null);
    trigger.current?.focus();
  }

  async function refresh() {
    await Promise.all([
      queries.invalidateQueries({ queryKey: ["entries", account.id, entry.userWineId] }),
      queries.invalidateQueries({ queryKey: ["wine", account.id, entry.userWineId] }),
      queries.invalidateQueries({ queryKey: ["wines", account.id] }),
      queries.invalidateQueries({ queryKey: ["occasion-wines", account.id] }),
    ]);
  }

  async function remove() {
    if (!selected || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      try {
        await api.call((client, signal) =>
          client.DELETE("/api/v1/entries/{entry_id}", {
            params: {
              path: { entry_id: selected.entry.id },
              query: { version: selected.entry.version ?? 1 },
            },
            signal,
          }),
        );
      } catch (failure) {
        // A repeated request after a lost success response sees an already absent entry.
        if (!(failure instanceof RequestFailure) || failure.status !== 404) throw failure;
      }
      storeEditDraft(editKey(account.id, selected.entry.id), null);
      closeDialog();
      await refresh();
      document.getElementById("history-title")?.focus();
    } catch (failure) {
      if (failure instanceof RequestFailure && failure.status === 409) {
        closeDialog();
        setError(
          "This entry changed or another save is in progress. Review the entry and choose Delete entry again.",
        );
        await refresh();
      } else {
        setError(
          failure instanceof RequestFailure && failure.status === 401
            ? "Your session has ended. Sign in again before deleting."
            : failure instanceof RequestFailure && failure.status === 403
              ? "This account is unavailable. No further deletion can be requested."
              : "We couldn’t confirm the deletion. Retry to check; only this entry is affected.",
        );
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className="text-button delete-entry-trigger"
        onClick={() => {
          setError("");
          setSelected({ entry, label });
        }}
      >
        Delete entry
      </button>
      {!selected && error && <p role="alert">{error}</p>}
      {selected && (
        <dialog
          ref={dialog}
          className="entry-delete-dialog"
          aria-labelledby={`${id}-title`}
          aria-describedby={`${id}-description`}
          onCancel={(event) => {
            event.preventDefault();
            if (!busy) closeDialog();
          }}
        >
          <h2 id={`${id}-title`}>Delete this drinking entry?</h2>
          <p className="delete-entry-label">{selected.label}</p>
          {selected.entry.localTime && (
            <p>
              {selected.entry.localTime.slice(0, 5)} · {selected.entry.timezone}
            </p>
          )}
          {selected.entry.locationLabel && <p>{selected.entry.locationLabel}</p>}
          {selected.entry.notes && (
            <p className="entry-notes">
              {selected.entry.notes.slice(0, 200)}
              {selected.entry.notes.length > 200 ? "…" : ""}
            </p>
          )}
          <p id={`${id}-description`}>
            This entry and its notes will be permanently deleted. The wine record and its other
            entries will stay.
          </p>
          {error && <p role="alert">{error}</p>}
          <div className="capture-actions">
            <button
              ref={cancel}
              type="button"
              className="button button-secondary"
              disabled={busy}
              onClick={closeDialog}
            >
              Keep entry
            </button>
            <button type="button" className="button" disabled={busy} onClick={() => void remove()}>
              {busy ? "Deleting…" : "Delete this entry"}
            </button>
          </div>
        </dialog>
      )}
    </>
  );
}
