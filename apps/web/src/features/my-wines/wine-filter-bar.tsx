"use client";

import { useId } from "react";
import {
  ratingFilters,
  readWineFilters,
  vintageFilters,
  wineSorts,
  type WineFilters,
} from "./wine-filters";

export function WineFilterBar({
  filters,
  apply,
}: {
  filters: WineFilters;
  apply: (filters: WineFilters) => void;
}) {
  const id = useId();
  return (
    <form
      className="wine-filter-bar"
      role="search"
      aria-label="Search your wines"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const params = new URLSearchParams();
        for (const field of ["q", "sort", "rating", "vintage"])
          params.set(field, String(data.get(field) ?? ""));
        apply(readWineFilters(params));
      }}
    >
      <div className="wine-search-field">
        <label htmlFor={`${id}-query`}>Search wines</label>
        <input
          id={`${id}-query`}
          type="search"
          name="q"
          maxLength={200}
          defaultValue={filters.q}
          placeholder="Wine, producer, edition or year"
        />
      </div>
      <div className="wine-filter-fields">
        <div>
          <label htmlFor={`${id}-rating`}>Rating status</label>
          <select id={`${id}-rating`} name="rating" defaultValue={filters.rating}>
            {Object.entries(ratingFilters).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${id}-vintage`}>Vintage type</label>
          <select id={`${id}-vintage`} name="vintage" defaultValue={filters.vintage}>
            {Object.entries(vintageFilters).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${id}-sort`}>Sort by</label>
          <select id={`${id}-sort`} name="sort" defaultValue={filters.sort}>
            {Object.entries(wineSorts).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <button className="button" type="submit">
          Apply
        </button>
      </div>
    </form>
  );
}
