import Link from "next/link";
import { browseCatalog } from "@/features/catalog/api";
import { CatalogUnavailable, vintageLabel } from "@/features/catalog/catalog-display";
import { browseHref, catalogSearch } from "@/features/catalog/navigation";

export default async function BrowsePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const search = catalogSearch(await searchParams);
  const page = search ? await browseCatalog(search.q, search.offset) : null;
  const href = search ? browseHref(search.q, search.offset) : "/browse";
  return (
    <main id="main" className="page-content">
      <div className="journal-page-head">
        <div>
          <h1>Browse wines</h1>
          <p className="page-intro">A little curiosity. Your next discovery.</p>
        </div>
        <Link className="button button-secondary" href="/capture">
          Add wine manually
        </Link>
      </div>
      <form action="/browse" className="catalog-search" role="search">
        <div>
          <label htmlFor="catalog-query">Search the wine library</label>
          <input
            id="catalog-query"
            name="q"
            type="search"
            maxLength={200}
            defaultValue={search?.q ?? ""}
            placeholder="Wine, producer, vintage or edition"
          />
        </div>
        <button className="button" type="submit">
          Search
        </button>
      </form>
      {!search ? (
        <section className="empty-state">
          <h2>That search link isn’t valid.</h2>
          <p>Try a wine or producer name, using up to 200 characters.</p>
          <Link className="text-link" href="/browse">
            Start a new search
          </Link>
        </section>
      ) : !page ? (
        <CatalogUnavailable href={href} />
      ) : (
        <>
          <div className="catalog-results-heading">
            <h2>{search.q ? `Results for “${search.q}”` : "Explore the library"}</h2>
            {search.q && (
              <Link className="text-link" href="/browse">
                Clear search
              </Link>
            )}
          </div>
          <p className="catalog-caption">
            Each vintage and edition has its own page. Ordered by producer, then wine and newest
            vintage.
          </p>
          {page.items.length ? (
            <ul className="catalog-list" aria-label="Wine search results">
              {page.items.map((wine) => (
                <li key={wine.id}>
                  <Link
                    className="catalog-wine"
                    href={`/browse/${wine.id}?${new URLSearchParams({ q: search.q, offset: String(search.offset) })}`}
                    prefetch={false}
                  >
                    <div>
                      <h3>{wine.name}</h3>
                      <p className="wine-producer">{wine.producer}</p>
                    </div>
                    <p className="wine-release">{vintageLabel(wine)}</p>
                    <span className="catalog-open" aria-hidden="true">
                      View wine →
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <section className="empty-state">
              <h2>{search.q ? "No matching wines yet." : "No wines on this page yet."}</h2>
              <p>Our library is still growing. Try another search, or add your bottle manually.</p>
              <Link className="button button-secondary" href="/capture">
                Add wine manually
              </Link>
            </section>
          )}
          <nav className="catalog-pagination" aria-label="Wine result pages">
            {search.offset > 0 && (
              <Link
                className="button button-secondary"
                href={browseHref(search.q, Math.max(0, search.offset - 24))}
              >
                Previous wines
              </Link>
            )}
            {page.nextOffset !== null && (
              <Link
                className="button button-secondary"
                href={browseHref(search.q, page.nextOffset)}
              >
                Next wines
              </Link>
            )}
          </nav>
        </>
      )}
    </main>
  );
}
