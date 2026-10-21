import { vintageLabel } from "@/features/catalog/catalog-display";
import type { components } from "@/lib/api/schema";

export function BarcodeCandidates({
  candidates,
  selected,
  onSelect,
}: {
  candidates: components["schemas"]["BarcodeCandidate"][];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <fieldset className="barcode-options">
      <legend>Which vintage and edition are on your bottle?</legend>
      {candidates.map((candidate) => (
        <section
          className="barcode-candidate"
          key={candidate.definitionId}
          aria-labelledby={`candidate-${candidate.definitionId}`}
        >
          <h3 id={`candidate-${candidate.definitionId}`}>{candidate.name}</h3>
          <p>{candidate.producer}</p>
          <p className="catalog-caption">
            Recorded bottle sizes: {candidate.bottleSizesMl.map((size) => `${size} ml`).join(", ")}
          </p>
          {candidate.releases.map((wine) => (
            <label className="barcode-option" key={wine.id}>
              <input
                type="radio"
                name="release"
                value={wine.id}
                required
                checked={selected === wine.id}
                onChange={() => onSelect(wine.id)}
              />
              {vintageLabel(wine)}
            </label>
          ))}
          {!candidate.releases.length && (
            <p>No vintages are listed yet. Search by name or add your bottle manually.</p>
          )}
          <details className="barcode-sources">
            <summary>Barcode references</summary>
            <ul>
              {candidate.sources.map((source) => (
                <li key={source.url}>
                  <a
                    className="text-link"
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {new URL(source.url).hostname} (opens in a new tab)
                  </a>{" "}
                  — recorded <time dateTime={source.retrievedOn}>{source.retrievedOn}</time>
                </li>
              ))}
            </ul>
          </details>
        </section>
      ))}
    </fieldset>
  );
}
