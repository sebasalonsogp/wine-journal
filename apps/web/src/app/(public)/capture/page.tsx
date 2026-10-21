import { CaptureForm } from "@/features/capture/capture-form";
import { uuid } from "@/features/capture/draft";
import Link from "next/link";
import { catalogDetails } from "@/features/catalog/api";
import { CatalogUnavailable } from "@/features/catalog/catalog-display";

export default async function CapturePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { wine, catalog } = await searchParams;
  if (catalog !== undefined) {
    const result =
      typeof catalog === "string" && uuid.test(catalog) && wine === undefined
        ? await catalogDetails(catalog)
        : ({ kind: "missing" } as const);
    if (result.kind !== "found") {
      return (
        <main id="main" className="page-content">
          <h1>Choose a wine to record</h1>
          {result.kind === "unavailable" ? (
            <CatalogUnavailable
              href={`/capture?${new URLSearchParams({ catalog: String(catalog) })}`}
            />
          ) : (
            <p>
              This wine selection is unavailable. Search the library or continue your unfinished
              entry.
            </p>
          )}
          <p>
            <Link className="text-link" href="/browse">
              Search wines
            </Link>
          </p>
          <p>
            <Link className="text-link" href="/capture">
              Continue my unfinished entry
            </Link>
          </p>
        </main>
      );
    }
    return <CaptureForm key={result.wine.id} catalogWine={result.wine} />;
  }
  return (
    <CaptureForm
      key={typeof wine === "string" ? wine : "manual"}
      wineId={typeof wine === "string" && uuid.test(wine) ? wine : undefined}
    />
  );
}
