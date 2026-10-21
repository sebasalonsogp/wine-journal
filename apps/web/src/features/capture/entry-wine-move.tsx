"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { dateLabel, releaseLabel, type Wine } from "@/features/my-wines/wine-display";
import { WineSelect } from "@/features/my-wines/wine-select";
import { RequestFailure } from "@/lib/session/http";
import { CaptureFields } from "./capture-fields";
import { entryBody, newDraft } from "./draft";
import type { Entry } from "./edit-draft";

type Phase = "choose" | "confirm" | "uncertain" | "review" | "saved";

export function EntryWineMove({
  entry,
  source,
  pendingPhotos,
  close,
}: {
  entry: Entry;
  source: Wine;
  pendingPhotos: boolean;
  close: () => void;
}) {
  const api = useJournalApi();
  const account = useAccount()!;
  const queries = useQueryClient();
  const [original, setOriginal] = useState(entry);
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [selected, setSelected] = useState<Wine | null>(null);
  const [fields, setFields] = useState(() => newDraft(account.id).fields);
  const [phase, setPhase] = useState<Phase>("choose");
  const [latest, setLatest] = useState<{ entry: Entry; wine: Wine } | null>(null);
  const [saved, setSaved] = useState<Entry | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  const targetLabel =
    mode === "existing" && selected
      ? `${selected.name} · ${releaseLabel(selected)}`
      : `${fields.name.trim()} · ${fields.vintageStatus === "YEAR" ? fields.year : fields.vintageStatus.replaceAll("_", " ").toLowerCase()}${fields.edition.trim() ? ` · ${fields.edition.trim()}` : ""}`;

  async function refresh() {
    await Promise.allSettled(
      [
        "entries",
        "wine",
        "wines",
        "move-wines",
        "occasion-wines",
        "wine-moments",
        "occasion-album",
        "album-sources",
      ].map((name) => queries.invalidateQueries({ queryKey: [name, account.id] })),
    );
  }
  async function review() {
    setBusy(true);
    setError("");
    try {
      const current = await api.call((client, signal) =>
        client.GET("/api/v1/entries/{entry_id}", {
          params: { path: { entry_id: entry.id } },
          signal,
        }),
      );
      const wine = await api.call((client, signal) =>
        client.GET("/api/v1/me/wines/{wine_id}", {
          params: { path: { wine_id: current.userWineId } },
          signal,
        }),
      );
      setLatest({ entry: current, wine });
      setPhase("review");
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "We couldn’t check the entry. Try again.",
      );
      setPhase("uncertain");
    } finally {
      setBusy(false);
    }
  }
  async function move() {
    if (
      submitting.current ||
      pendingPhotos ||
      phase !== "confirm" ||
      (mode === "existing" && !selected)
    )
      return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await api.call((client, signal) =>
        client.PUT("/api/v1/entries/{entry_id}/wine", {
          params: { path: { entry_id: entry.id } },
          body: {
            version: original.version ?? 1,
            previousWineId: original.userWineId,
            ...(mode === "existing"
              ? { wineId: selected!.id }
              : { manualWine: entryBody(fields).manualWine }),
          },
          signal,
        }),
      );
      setSaved(result);
      setPhase("saved");
      await refresh();
    } catch (failure) {
      if (failure instanceof RequestFailure && [404, 422].includes(failure.status)) {
        setError(failure.message);
        setPhase("choose");
      } else {
        setPhase("uncertain");
        setError("We couldn’t confirm the move. Check the saved entry before trying again.");
        if (failure instanceof RequestFailure && failure.status === 409) await review();
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  const movedElsewhere = latest && latest.entry.userWineId !== original.userWineId;
  return (
    <section className="entry-editor" aria-label="Move drinking entry">
      <h2 ref={heading} tabIndex={-1}>
        Move to another wine
      </h2>
      <p>
        {dateLabel(original.consumedDate)} · From {source.name} · {releaseLabel(source)}
      </p>
      <p>
        This entry’s date, notes, occasion and saved photos stay with it. Ratings, rating history
        and bottle covers stay with their wine records.
      </p>
      {pendingPhotos && (
        <p role="status">
          Save photo captions and finish or remove selected files for this entry before moving it.
        </p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (phase === "choose" && (mode === "new" || selected)) setPhase("confirm");
        }}
      >
        {phase === "choose" && (
          <fieldset disabled={busy}>
            <legend>Choose the correct bottle</legend>
            <div className="capture-actions">
              <button
                type="button"
                className="button button-secondary"
                aria-pressed={mode === "existing"}
                onClick={() => setMode("existing")}
              >
                Choose from My wines
              </button>
              <button
                type="button"
                className="button button-secondary"
                aria-pressed={mode === "new"}
                onClick={() => setMode("new")}
              >
                Enter a new wine
              </button>
            </div>
            {mode === "existing" ? (
              <WineSelect sourceId={original.userWineId} selected={selected} select={setSelected} />
            ) : (
              <CaptureFields
                fields={fields}
                change={(values) => setFields({ ...fields, ...values })}
                showDate={false}
                idPrefix={`move-${entry.id}-`}
              />
            )}
            {mode === "new" && (
              <p>A new private wine record will be created. Matching names are not merged.</p>
            )}
            <button
              className="button"
              type="submit"
              disabled={pendingPhotos || (mode === "existing" && !selected)}
            >
              Review move
            </button>
          </fieldset>
        )}
      </form>
      {phase === "confirm" && (
        <section aria-label="Confirm wine move">
          <h3>Move this entry to {targetLabel}?</h3>
          <p>{mode === "existing" ? selected?.producer : fields.producer}</p>
          <p>Other entries under {source.name} will stay where they are.</p>
          <div className="capture-actions">
            <button
              type="button"
              className="button"
              disabled={busy || pendingPhotos}
              onClick={() => void move()}
            >
              {busy ? "Moving…" : "Confirm move"}
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => setPhase("choose")}
            >
              Change destination
            </button>
          </div>
        </section>
      )}
      {phase === "uncertain" && (
        <button type="button" className="button" disabled={busy} onClick={() => void review()}>
          Check saved entry
        </button>
      )}
      {phase === "review" && latest && (
        <section className="edit-conflict" aria-label="Latest saved entry">
          <h3>Review the saved entry</h3>
          <p role="status">
            Your selection is kept. The saved entry is currently with {latest.wine.name} ·{" "}
            {releaseLabel(latest.wine)}.
          </p>
          <p>
            {dateLabel(latest.entry.consumedDate)}
            {latest.entry.localTime
              ? ` · ${latest.entry.localTime.slice(0, 5)} · ${latest.entry.timezone}`
              : ""}
          </p>
          {latest.entry.locationLabel && <p>{latest.entry.locationLabel}</p>}
          {latest.entry.notes && <p className="entry-notes">{latest.entry.notes}</p>}
          {latest.entry.occasionId && (
            <Link href={`/occasions/${latest.entry.occasionId}`} prefetch={false}>
              View current occasion
            </Link>
          )}
          <p>
            <Link
              className="text-link"
              href={`/my-wines/${latest.entry.userWineId}?entry=${entry.id}`}
              prefetch={false}
            >
              View saved entry
            </Link>
          </p>
          {movedElsewhere ? (
            <p>
              The wine has changed. Open the saved entry to review it before starting another move.
            </p>
          ) : (
            <button
              type="button"
              className="button"
              disabled={busy || pendingPhotos}
              onClick={() => {
                setOriginal(latest.entry);
                setPhase("confirm");
              }}
            >
              Review move using this version
            </button>
          )}
        </section>
      )}
      {phase === "saved" && saved && (
        <div role="status">
          <p>Entry moved to {targetLabel}.</p>
          <Link
            className="text-link"
            href={`/my-wines/${saved.userWineId}?entry=${saved.id}`}
            prefetch={false}
          >
            View moved entry
          </Link>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      <button
        type="button"
        className="text-button"
        disabled={busy}
        onClick={() => {
          close();
          void refresh();
        }}
      >
        {phase === "saved" ? "Close move details" : "Close without another change"}
      </button>
    </section>
  );
}
