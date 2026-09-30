"use client";

import { useEffect, useId, useState } from "react";
import type { createTransport } from "@/lib/api/transport";
import { dateLabel } from "@/features/my-wines/wine-display";
import type { Occasion } from "./occasion-draft";

export function ExistingOccasions({
  api,
  id,
  selected,
  select,
}: {
  api: ReturnType<typeof createTransport>;
  id?: string;
  selected: string | null;
  select: (id: string | null, label: string) => void;
}) {
  const generatedId = useId();
  const controlId = id ?? generatedId;
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
      <label htmlFor={controlId}>Choose an occasion</label>
      <select
        id={controlId}
        value={selected ?? ""}
        onChange={(event) =>
          select(event.target.value || null, event.target.selectedOptions[0].text)
        }
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
        <p>No occasions yet. Create one in the Occasions tab, or while logging a wine.</p>
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
