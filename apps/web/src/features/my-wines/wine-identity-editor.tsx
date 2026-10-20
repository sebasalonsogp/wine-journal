"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { CaptureFields } from "@/features/capture/capture-fields";
import { entryBody, newDraft, type Fields } from "@/features/capture/draft";
import type { components } from "@/lib/api/schema";
import { RequestFailure } from "@/lib/session/http";
import { releaseLabel } from "./wine-display";

type Wine = components["schemas"]["WineResponse"];
type Phase = "edit" | "confirm" | "uncertain" | "review";

export function WineIdentityEditor({ wine }: { wine: Wine }) {
  const account = useAccount()!;
  const api = useJournalApi();
  const queries = useQueryClient();
  const [draft, setDraft] = useState<{ fields: Fields; version: number } | null>(null);
  const [phase, setPhase] = useState<Phase>("edit");
  const [latest, setLatest] = useState<Wine | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const submitting = useRef(false);
  const opener = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const editing = draft !== null;
  useEffect(() => {
    if (editing) heading.current?.focus();
  }, [editing, phase]);

  async function refresh() {
    await Promise.all(
      [
        "wine",
        "wines",
        "move-wines",
        "occasion-wines",
        "wine-moments",
        "occasion-album",
        "album-sources",
      ].map((key) => queries.invalidateQueries({ queryKey: [key, account.id] })),
    );
  }
  function close() {
    setDraft(null);
    setLatest(null);
    setError("");
    requestAnimationFrame(() => opener.current?.focus());
  }
  async function saved() {
    close();
    setNotice("Wine details saved. All tastings under this wine use these details.");
    await refresh();
  }
  async function checkSaved() {
    if (!draft) return;
    setBusy(true);
    setError("");
    try {
      const current = await api.call((client, signal) =>
        client.GET("/api/v1/me/wines/{wine_id}", {
          params: { path: { wine_id: wine.id } },
          signal,
        }),
      );
      const proposed = entryBody(draft.fields).manualWine!;
      if (
        current.name === proposed.name &&
        current.producer === proposed.producer &&
        current.vintageStatus === proposed.vintageStatus &&
        current.year === proposed.year &&
        current.edition === proposed.edition
      ) {
        await saved();
      } else {
        setLatest(current);
        setPhase("review");
      }
    } catch (failure) {
      setError(
        failure instanceof RequestFailure
          ? failure.message
          : "We couldn’t check the saved wine. Try again.",
      );
      setPhase("uncertain");
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    if (!draft || submitting.current || phase !== "confirm") return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      await api.call((client, signal) =>
        client.PUT("/api/v1/me/wines/{wine_id}/identity", {
          params: { path: { wine_id: wine.id } },
          body: { version: draft.version, wine: entryBody(draft.fields).manualWine! },
          signal,
        }),
      );
      await saved();
    } catch (failure) {
      if (failure instanceof RequestFailure && failure.status === 422) {
        setError("Check the wine name and vintage. Your changes are kept.");
        setPhase("edit");
      } else {
        setError("We couldn’t confirm the correction. Check the saved wine before trying again.");
        setPhase("uncertain");
        if (failure instanceof RequestFailure && failure.status === 409) await checkSaved();
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  if (!draft)
    return (
      <div className="entry-controls">
        {wine.canEditIdentity ? (
          <button
            className="text-button"
            ref={opener}
            onClick={() => {
              setNotice("");
              setPhase("edit");
              setDraft({
                version: wine.identityVersion ?? 0,
                fields: {
                  ...newDraft(account.id).fields,
                  name: wine.name,
                  producer: wine.producer ?? "",
                  edition: wine.edition ?? "",
                  vintageStatus: wine.vintageStatus as Fields["vintageStatus"],
                  year: wine.year?.toString() ?? "",
                },
              });
            }}
          >
            Correct wine details
          </button>
        ) : (
          <p>
            These label details are protected. If a tasting belongs to another wine, move it from
            your drinking history.
          </p>
        )}
        {notice && <p role="status">{notice}</p>}
      </div>
    );

  return (
    <section className="entry-editor" aria-label="Correct wine details" aria-busy={busy}>
      <h2 tabIndex={-1} ref={heading}>
        Correct wine details
      </h2>
      <p>
        This changes the shared label details for all {wine.entryCount} tasting
        {wine.entryCount === 1 ? "" : "s"} under this wine, including those linked to occasions.
        Ratings, memories and bottle cover stay attached. Matching wine records are not merged.
      </p>
      <p>
        If only one tasting belongs to a different bottle, use “Move to another wine” in its history
        entry.
      </p>
      {phase === "edit" && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setPhase("confirm");
          }}
        >
          <fieldset disabled={busy}>
            <legend>Details from the bottle label</legend>
            <CaptureFields
              fields={draft.fields}
              change={(values) => setDraft({ ...draft, fields: { ...draft.fields, ...values } })}
              idPrefix="identity-"
              showDate={false}
            />
            <button className="button" type="submit">
              Review correction
            </button>
          </fieldset>
        </form>
      )}
      {phase === "confirm" && (
        <div>
          <h3>Save these label details?</h3>
          <p>
            {draft.fields.name} ·{" "}
            {releaseLabel({
              ...wine,
              vintageStatus: draft.fields.vintageStatus,
              year: draft.fields.vintageStatus === "YEAR" ? Number(draft.fields.year) : null,
              edition: draft.fields.edition,
            })}
          </p>
          {draft.fields.producer && <p>{draft.fields.producer}</p>}
          <div className="capture-actions">
            <button type="button" className="button" disabled={busy} onClick={() => void save()}>
              {busy ? "Saving…" : "Confirm correction"}
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => setPhase("edit")}
            >
              Keep editing
            </button>
          </div>
        </div>
      )}
      {phase === "uncertain" && (
        <button type="button" className="button" disabled={busy} onClick={() => void checkSaved()}>
          Check saved wine
        </button>
      )}
      {phase === "review" && latest && (
        <section className="edit-conflict" aria-label="Latest saved wine">
          <h3>Review the saved wine</h3>
          <p role="status">
            Your changes are kept. Currently saved: {latest.name} · {releaseLabel(latest)}.
          </p>
          <p>{latest.producer || "No producer entered"}</p>
          {latest.canEditIdentity ? (
            <button
              type="button"
              className="button"
              disabled={busy}
              onClick={() => {
                setDraft({ ...draft, version: latest.identityVersion ?? 0 });
                setPhase("confirm");
              }}
            >
              Review my correction using this version
            </button>
          ) : (
            <p>These details can no longer be edited here.</p>
          )}
        </section>
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
        Close without another change
      </button>
    </section>
  );
}
