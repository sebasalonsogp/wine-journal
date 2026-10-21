import Link from "next/link";
import type { components } from "@/lib/api/schema";

export function vintageLabel(wine: components["schemas"]["CatalogWine"]) {
  const vintage =
    wine.vintageStatus === "YEAR"
      ? String(wine.year)
      : wine.vintageStatus === "NON_VINTAGE"
        ? "Non-vintage"
        : "Multi-vintage";
  return [vintage, wine.edition].filter(Boolean).join(" · ");
}

export function CatalogUnavailable({ href }: { href: string }) {
  return (
    <section className="empty-state" aria-labelledby="catalog-unavailable">
      <h2 id="catalog-unavailable">The wine library is unavailable.</h2>
      <p>We couldn’t load the wines. Please try again in a moment.</p>
      <a className="button button-secondary" href={href}>
        Try again
      </a>
      <p>
        You can still{" "}
        <Link className="text-link" href="/capture">
          add a wine manually
        </Link>
        .
      </p>
    </section>
  );
}
