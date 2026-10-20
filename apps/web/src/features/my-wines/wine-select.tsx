"use client";

import { useId, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { releaseLabel, type Wine } from "./wine-display";

export function WineSelect({
  sourceId,
  selected,
  select,
}: {
  sourceId: string;
  selected: Wine | null;
  select: (wine: Wine | null) => void;
}) {
  const id = useId();
  const api = useJournalApi();
  const account = useAccount()!;
  const [text, setText] = useState("");
  const [search, setSearch] = useState("");
  const query = useInfiniteQuery({
    queryKey: ["move-wines", account.id, search],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      api.call((client, signal) =>
        client.GET("/api/v1/me/wines", {
          params: { query: { q: search, cursor: pageParam, limit: 20 } },
          signal,
        }),
      ),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
  });
  const items = (query.data?.pages.flatMap((page) => page.items) ?? []).filter(
    (wine) => wine.id !== sourceId,
  );
  return (
    <>
      <div className="form-field">
        <label htmlFor={`${id}-search`}>Search your wines</label>
        <input
          id={`${id}-search`}
          type="search"
          maxLength={200}
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button type="button" className="text-button" onClick={() => setSearch(text.trim())}>
          Search wines
        </button>
      </div>
      <div className="form-field">
        <label htmlFor={id}>Destination wine</label>
        <select
          id={id}
          required
          value={selected?.id ?? ""}
          onChange={(event) => select(items.find((wine) => wine.id === event.target.value) ?? null)}
        >
          <option value="">Choose a wine</option>
          {selected && !items.some((wine) => wine.id === selected.id) && (
            <option value={selected.id}>
              {selected.name} · {releaseLabel(selected)}
            </option>
          )}
          {items.map((wine) => (
            <option key={wine.id} value={wine.id}>
              {wine.name} · {releaseLabel(wine)}
              {wine.producer ? ` · ${wine.producer}` : ""}
            </option>
          ))}
        </select>
      </div>
      {query.isFetching && <p role="status">Loading wines…</p>}
      {query.error && <p role="alert">We couldn’t load wines. Your selection is kept.</p>}
      {query.error && (
        <button
          type="button"
          className="text-button"
          disabled={query.isFetching}
          onClick={() => void (query.hasNextPage ? query.fetchNextPage() : query.refetch())}
        >
          Try loading wines again
        </button>
      )}
      {!query.isPending && !query.error && !items.length && (
        <p>No other wines found. Try another search or enter a new wine.</p>
      )}
      {query.hasNextPage && (
        <button
          type="button"
          className="text-button"
          disabled={query.isFetching}
          onClick={() => void query.fetchNextPage()}
        >
          Load more wines
        </button>
      )}
    </>
  );
}
