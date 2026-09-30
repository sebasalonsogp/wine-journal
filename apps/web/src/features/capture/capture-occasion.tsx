"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { type createTransport } from "@/lib/api/transport";
import { dateLabel } from "@/features/my-wines/wine-display";
import { newOccasionDraft, type Occasion } from "@/features/occasions/occasion-draft";
import { OccasionFields } from "@/features/occasions/occasion-fields";
import type { Fields } from "./draft";

export function CaptureOccasion({
  fields,
  change,
  owner,
  api,
}: {
  fields: Fields;
  change: (values: Partial<Fields>) => void;
  owner: string | null;
  api: ReturnType<typeof createTransport>;
}) {
  const [choosing, setChoosing] = useState(Boolean(fields.occasionId));
  return (
    <section className="capture-occasion" aria-labelledby="capture-occasion-title">
      <h2 id="capture-occasion-title">
        An occasion <span>optional</span>
      </h2>
      <p>Keep this glass on its own, or remember it as part of a bigger moment.</p>
      {fields.newOccasion ? (
        <>
          <OccasionFields
            draft={fields.newOccasion}
            disabled={false}
            change={(newOccasion) => change({ newOccasion })}
          />
          <button
            type="button"
            className="text-button"
            onClick={() => change({ newOccasion: null })}
          >
            Cancel new occasion
          </button>
          <p className="form-footnote">
            The new occasion and this wine entry will be saved together.
          </p>
        </>
      ) : choosing && owner ? (
        <>
          <ExistingOccasions
            key={owner}
            api={api}
            selected={fields.occasionId}
            select={(occasionId) => change({ occasionId })}
          />
          <button
            type="button"
            className="text-button"
            onClick={() => {
              change({ occasionId: null });
              setChoosing(false);
            }}
          >
            Keep without an occasion
          </button>
        </>
      ) : (
        <div className="capture-actions">
          {owner ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={() => setChoosing(true)}
            >
              Choose existing occasion
            </button>
          ) : (
            <Link href="/auth/sign-in?next=%2Fcapture">Sign in to choose an occasion</Link>
          )}
          <button
            type="button"
            className="button button-secondary"
            onClick={() => {
              change({
                occasionId: null,
                newOccasion: { ...newOccasionDraft(), occasionDate: fields.consumedDate },
              });
              setChoosing(false);
            }}
          >
            Create new occasion
          </button>
        </div>
      )}
    </section>
  );
}

function ExistingOccasions({
  api,
  selected,
  select,
}: {
  api: ReturnType<typeof createTransport>;
  selected: string | null;
  select: (id: string | null) => void;
}) {
  const [items, setItems] = useState<Occasion[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    void api
      .call((client, signal) =>
        client.GET("/api/v1/occasions", { params: { query: { limit: 20 } }, signal }),
      )
      .then((page) => {
        if (active) {
          setItems(page.items);
          setCursor(page.nextCursor);
          setError("");
        }
      })
      .catch(() => {
        if (active) setError("We couldn’t load your occasions. Your wine details are kept.");
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [api, attempt]);

  async function more() {
    if (!cursor || busy) return;
    setBusy(true);
    setError("");
    try {
      const page = await api.call((client, signal) =>
        client.GET("/api/v1/occasions", { params: { query: { limit: 20, cursor } }, signal }),
      );
      setItems((previous) => [
        ...previous,
        ...page.items.filter((item) => !previous.some((old) => old.id === item.id)),
      ]);
      setCursor(page.nextCursor);
    } catch {
      setError("We couldn’t load more occasions. Try again when you’re connected.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-field">
      <label htmlFor="existing-occasion">Choose an occasion</label>
      <select
        id="existing-occasion"
        value={selected ?? ""}
        onChange={(event) => select(event.target.value || null)}
      >
        <option value="">No occasion</option>
        {selected && !items.some((item) => item.id === selected) && (
          <option value={selected}>Your selected occasion</option>
        )}
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.title ? `${item.title} · ` : ""}
            {dateLabel(item.occasionDate)}
          </option>
        ))}
      </select>
      {busy && <p role="status">Loading occasions…</p>}
      {error && <p role="alert">{error}</p>}
      {error && !items.length && (
        <button
          type="button"
          className="text-button"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            setAttempt((value) => value + 1);
          }}
        >
          Try loading occasions again
        </button>
      )}
      {!busy && !error && !items.length && (
        <p>No occasions yet. You can create one from this entry.</p>
      )}
      {cursor && (
        <button type="button" className="text-button" disabled={busy} onClick={() => void more()}>
          Load more occasions
        </button>
      )}
      <p className="form-footnote">Your wine’s date and notes stay as entered.</p>
    </div>
  );
}
