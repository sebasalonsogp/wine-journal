"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import type { Entry } from "@/features/capture/edit-draft";
import { dateLabel } from "@/features/my-wines/wine-display";
import { RequestFailure } from "@/lib/session/http";
import { ExistingOccasions } from "./occasion-select";

type Selection = { original: Entry; target: string | null; label: string };

export function EntryOccasion({ entry }: { entry: Entry }) {
  const api = useJournalApi();
  const account = useAccount()!;
  const queries = useQueryClient();
  const [selection, setSelection] = useState<Selection | null>(null);
  const [latest, setLatest] = useState<Entry | null>(null);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const submitting = useRef(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const currentId = latest ? latest.occasionId : selection?.original.occasionId;
  const current = useQuery({
    queryKey: ["occasion", account.id, currentId],
    enabled: Boolean(selection && currentId),
    queryFn: () =>
      api.call((client, signal) =>
        client.GET("/api/v1/occasions/{occasion_id}", {
          params: { path: { occasion_id: currentId! } },
          signal,
        }),
      ),
  });

  async function refresh() {
    await Promise.all(
      ["entries", "occasion-wines"].map((name) =>
        queries.invalidateQueries({ queryKey: [name, account.id] }),
      ),
    );
  }
  function close() {
    setSelection(null);
    setLatest(null);
    setUncertain(false);
    setError("");
    requestAnimationFrame(() => trigger.current?.focus());
  }
  async function review() {
    setBusy(true);
    setError("");
    try {
      const saved = await api.call((client, signal) =>
        client.GET("/api/v1/entries/{entry_id}", {
          params: { path: { entry_id: entry.id } },
          signal,
        }),
      );
      setLatest(saved);
      setUncertain(false);
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "We couldn’t read the entry. Try checking again.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function save(original: Entry) {
    if (!selection || submitting.current) return;
    const target = selection.target;
    if (target === (original.occasionId ?? null)) {
      close();
      await refresh();
      return;
    }
    if (
      original.occasionId &&
      !window.confirm(
        target
          ? `Move this drinking entry from ${current.data?.title || "its current occasion"} to ${selection.label}? Its date, notes and wine rating will stay unchanged.`
          : "Remove this entry from its occasion? The drinking entry, notes and wine rating will stay in your journal.",
      )
    )
      return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      if (target) {
        await api.call((client, signal) =>
          client.PUT("/api/v1/occasions/{occasion_id}/entries/{entry_id}", {
            params: { path: { occasion_id: target, entry_id: entry.id } },
            body: {
              version: original.version ?? 1,
              previousOccasionId: original.occasionId ?? null,
            },
            signal,
          }),
        );
      } else {
        await api.call((client, signal) =>
          client.DELETE("/api/v1/occasions/{occasion_id}/entries/{entry_id}", {
            params: {
              path: { occasion_id: original.occasionId!, entry_id: entry.id },
              query: { version: original.version ?? 1 },
            },
            signal,
          }),
        );
      }
      close();
      setNotice(target ? "Occasion linked." : "Entry kept without an occasion.");
      await refresh();
    } catch (failure) {
      if (failure instanceof RequestFailure && failure.status === 409) {
        setUncertain(true);
        await review();
      } else {
        setUncertain(true);
        setError(
          failure instanceof RequestFailure && [401, 403, 404].includes(failure.status)
            ? failure.message
            : "We couldn’t confirm the change. Check the saved entry before trying again.",
        );
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="entry-occasion">
      <button
        ref={trigger}
        type="button"
        className="text-button"
        hidden={Boolean(selection)}
        onClick={() => {
          setNotice("");
          setSelection({
            original: entry,
            target: entry.occasionId ?? null,
            label: "your selected occasion",
          });
        }}
      >
        Organize occasion
      </button>
      {selection && (
        <form
          className="entry-editor"
          aria-label="Organize entry occasion"
          onSubmit={(event) => {
            event.preventDefault();
            if (!latest && !uncertain) void save(selection.original);
          }}
        >
          <h3>Occasion for this entry</h3>
          <p>{dateLabel(selection.original.consumedDate)} · Only the occasion link changes.</p>
          <p>
            Current occasion:{" "}
            {currentId ? (
              <Link href={`/occasions/${currentId}`} prefetch={false}>
                {current.data?.title ||
                  (current.data ? dateLabel(current.data.occasionDate) : "View current occasion")}
              </Link>
            ) : (
              "None"
            )}
          </p>
          <fieldset disabled={busy || uncertain}>
            <legend className="sr-only">Choose the entry’s occasion</legend>
            <ExistingOccasions
              api={api}
              selected={selection.target}
              select={(target, label) => setSelection({ ...selection, target, label })}
            />
          </fieldset>
          {latest && (
            <section className="edit-conflict" aria-label="Latest entry">
              <h4>Review the latest entry</h4>
              <p role="alert">
                This entry may have changed while you were choosing. Your selection is kept; review
                before applying it.
              </p>
              <p>
                {dateLabel(latest.consumedDate)}
                {latest.localTime ? ` · ${latest.localTime.slice(0, 5)} · ${latest.timezone}` : ""}
              </p>
              {latest.locationLabel && <p>{latest.locationLabel}</p>}
              {latest.notes && <p className="entry-notes">{latest.notes}</p>}
              <div className="capture-actions">
                {selection.target !== (latest.occasionId ?? null) && (
                  <button
                    type="button"
                    className="button"
                    disabled={busy || uncertain}
                    onClick={() => void save(latest)}
                  >
                    Apply selection to latest entry
                  </button>
                )}
                <button
                  type="button"
                  className="text-button"
                  disabled={busy}
                  onClick={() => {
                    close();
                    void refresh();
                  }}
                >
                  Keep current occasion
                </button>
              </div>
            </section>
          )}
          {error && <p role="alert">{error}</p>}
          <div className="capture-actions">
            {uncertain ? (
              <button
                type="button"
                className="button"
                disabled={busy}
                onClick={() => void review()}
              >
                Check saved entry
              </button>
            ) : (
              !latest && (
                <button
                  type="submit"
                  className="button"
                  disabled={busy || selection.target === (selection.original.occasionId ?? null)}
                >
                  Save occasion link
                </button>
              )
            )}
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => {
                close();
                void refresh();
              }}
            >
              Cancel occasion change
            </button>
          </div>
        </form>
      )}
      {notice && <p role="status">{notice}</p>}
    </div>
  );
}
