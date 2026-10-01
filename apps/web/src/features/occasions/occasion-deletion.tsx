"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { dateLabel } from "@/features/my-wines/wine-display";
import { RequestFailure } from "@/lib/session/http";
import { occasionKey, storeOccasionDraft, type Occasion } from "./occasion-draft";

export function OccasionDeletion({ occasion }: { occasion: Occasion }) {
  const api = useJournalApi();
  const account = useAccount()!;
  const router = useRouter();
  const queries = useQueryClient();
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const submitting = useRef(false);
  const [selected, setSelected] = useState<Occasion | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!selected) return;
    const element = dialog.current!;
    element.showModal();
    cancel.current?.focus();
    return () => element.close();
  }, [selected]);

  function close() {
    dialog.current?.close();
    setSelected(null);
    trigger.current?.focus();
  }

  async function finish() {
    const key = occasionKey(account.id, occasion.id);
    storeOccasionDraft(key, null);
    storeOccasionDraft(`${key}:add-wines`, null);
    await Promise.all(
      ["occasions", "entries"].map((name) =>
        queries.invalidateQueries({ queryKey: [name, account.id] }),
      ),
    );
    close();
    router.replace("/occasions");
    queries.removeQueries({ queryKey: ["occasion", account.id, occasion.id], exact: true });
    queries.removeQueries({ queryKey: ["occasion-wines", account.id, occasion.id] });
  }

  async function remove() {
    if (!selected || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      await api.call((client, signal) =>
        client.DELETE("/api/v1/occasions/{occasion_id}", {
          params: { path: { occasion_id: selected.id }, query: { version: selected.version } },
          signal,
        }),
      );
      await finish();
    } catch (failure) {
      if (failure instanceof RequestFailure && failure.status === 404) {
        // The same request after a lost success response sees an absent occasion.
        await finish();
      } else if (failure instanceof RequestFailure && failure.status === 409) {
        try {
          const latest = await api.call((client, signal) =>
            client.GET("/api/v1/occasions/{occasion_id}", {
              params: { path: { occasion_id: selected.id } },
              signal,
            }),
          );
          queries.setQueryData(["occasion", account.id, occasion.id], latest);
          close();
          setError(
            "This occasion changed or another save is in progress. Review the saved details and choose Delete occasion again.",
          );
        } catch (readFailure) {
          if (readFailure instanceof RequestFailure && readFailure.status === 404) await finish();
          else
            setError(
              "We couldn’t load the latest occasion. Nothing further was deleted. Retry to review it.",
            );
        }
      } else {
        setError(
          failure instanceof RequestFailure && failure.status === 401
            ? "Your session has ended. Sign in again before deleting."
            : failure instanceof RequestFailure && failure.status === 403
              ? "This account is unavailable. No further deletion can be requested."
              : "We couldn’t confirm the deletion. Retry to check; your saved drinking entries stay in My Wines.",
        );
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <section aria-label="Remove occasion">
      <button
        ref={trigger}
        type="button"
        className="text-button"
        onClick={() => {
          setError("");
          setSelected(occasion);
        }}
      >
        Delete occasion
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
            if (!busy) close();
          }}
        >
          <h2 id={`${id}-title`}>Delete this occasion?</h2>
          <p className="delete-entry-label">{selected.title || dateLabel(selected.occasionDate)}</p>
          <p>
            {dateLabel(selected.occasionDate)}
            {selected.localTime
              ? ` · ${selected.localTime.slice(0, 5)} · ${selected.timezone}`
              : ""}
          </p>
          {selected.locationLabel && <p>{selected.locationLabel}</p>}
          {selected.notes && (
            <p className="entry-notes">
              {selected.notes.slice(0, 200)}
              {selected.notes.length > 200 ? "…" : ""}
            </p>
          )}
          <p id={`${id}-description`}>
            The occasion’s title, place and general notes will be permanently deleted. All saved
            drinking entries, their dates, personal notes and wine ratings will stay in My Wines
            without this occasion.
          </p>
          <p>Unsaved changes and wine drafts for this occasion will be discarded.</p>
          {error && <p role="alert">{error}</p>}
          <div className="capture-actions">
            <button
              ref={cancel}
              type="button"
              className="button button-secondary"
              disabled={busy}
              onClick={close}
            >
              Keep occasion
            </button>
            <button type="button" className="button" disabled={busy} onClick={() => void remove()}>
              {busy ? "Deleting…" : "Delete this occasion"}
            </button>
          </div>
        </dialog>
      )}
    </section>
  );
}
