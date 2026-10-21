import Link from "next/link";
import { notFound } from "next/navigation";
import { catalogDetails } from "@/features/catalog/api";
import { CatalogUnavailable, vintageLabel } from "@/features/catalog/catalog-display";
import { browseHref, catalogSearch } from "@/features/catalog/navigation";

export default async function CatalogWinePage({
  params,
  searchParams,
}: {
  params: Promise<{ wineId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { wineId } = await params;
  const search = catalogSearch(await searchParams);
  const back = search ? browseHref(search.q, search.offset) : "/browse";
  const result = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(wineId)
    ? await catalogDetails(wineId)
    : ({ kind: "missing" } as const);
  if (result.kind === "missing") notFound();
  return (
    <main id="main" className="page-content">
      <Link className="text-link" href={back}>
        Back to wines
      </Link>
      {result.kind === "unavailable" ? (
        <>
          <h1 className="journal-heading">Wine details</h1>
          <CatalogUnavailable href={`/browse/${encodeURIComponent(wineId)}`} />
        </>
      ) : (
        <>
          <header className="catalog-detail-head">
            <h1>{result.wine.name}</h1>
            <p className="catalog-producer">{result.wine.producer}</p>
            <p className="wine-release">{vintageLabel(result.wine)}</p>
            <div className="capture-actions">
              <Link className="button" href={`/capture?catalog=${result.wine.id}`} prefetch={false}>
                I tried this wine
              </Link>
            </div>
          </header>
          <div className="catalog-detail-columns">
            <section aria-labelledby="wine-facts">
              <h2 id="wine-facts">About this wine</h2>
              <dl className="catalog-facts">
                <div>
                  <dt>Producer</dt>
                  <dd>{result.wine.producer}</dd>
                </div>
                <div>
                  <dt>Vintage / edition</dt>
                  <dd>{vintageLabel(result.wine)}</dd>
                </div>
                <div>
                  <dt>Origin &amp; grapes</dt>
                  <dd>Not available yet</dd>
                </div>
                <div>
                  <dt>Tasting notes</dt>
                  <dd>Not available yet</dd>
                </div>
                <div>
                  <dt>Price &amp; where to buy</dt>
                  <dd>No verified offer available</dd>
                </div>
              </dl>
              <p className="catalog-caption">No bottle photo is available for this release yet.</p>
            </section>
            <section className="catalog-sources" aria-labelledby="wine-sources">
              <h2 id="wine-sources">From the producer</h2>
              <p>References for this wine’s identity. These are not verified shop offers.</p>
              {result.wine.sources.length ? (
                <ul>
                  {result.wine.sources.map((source) => (
                    <li key={source.url}>
                      <a
                        className="text-link"
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {new URL(source.url).hostname} (opens in a new tab)
                      </a>
                      <p className="catalog-caption">
                        Recorded <time dateTime={source.retrievedOn}>{source.retrievedOn}</time>
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No producer reference is available yet.</p>
              )}
              <p className="catalog-caption">Looking at a wine doesn’t add it to your journal.</p>
            </section>
          </div>
        </>
      )}
    </main>
  );
}
