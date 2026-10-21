import type { Fields } from "./draft";

export function CaptureFields({
  fields,
  change,
  idPrefix = "",
  showDate = true,
}: {
  fields: Fields;
  change: (values: Partial<Fields>) => void;
  idPrefix?: string;
  showDate?: boolean;
}) {
  const id = (name: string) => `${idPrefix}${name}`;
  return (
    <>
      {fields.releaseId || fields.catalogReleaseId ? (
        <div className="selected-wine">
          <h2>{fields.name}</h2>
          <p>{fields.producer}</p>
          <p>
            {fields.vintageStatus === "YEAR"
              ? fields.year
              : fields.vintageStatus.replaceAll("_", " ").toLowerCase()}
            {fields.edition ? ` · ${fields.edition}` : ""}
          </p>
        </div>
      ) : (
        <>
          <div className="form-field">
            <label htmlFor={id("wine-name")}>Wine name</label>
            <input
              id={id("wine-name")}
              required
              maxLength={200}
              value={fields.name}
              onChange={(event) => change({ name: event.target.value })}
              placeholder="The name on the label"
            />
          </div>
          <div className="capture-columns">
            <div className="form-field">
              <label htmlFor={id("vintage")}>Vintage</label>
              <select
                id={id("vintage")}
                value={fields.vintageStatus}
                onChange={(event) =>
                  change({ vintageStatus: event.target.value as Fields["vintageStatus"], year: "" })
                }
              >
                <option value="UNKNOWN">I’m not sure</option>
                <option value="YEAR">A specific year</option>
                <option value="NON_VINTAGE">Non-vintage</option>
                <option value="MULTI_VINTAGE">Multi-vintage</option>
              </select>
            </div>
            {fields.vintageStatus === "YEAR" && (
              <div className="form-field">
                <label htmlFor={id("year")}>Vintage year</label>
                <input
                  id={id("year")}
                  required
                  type="number"
                  min={1000}
                  max={9999}
                  step={1}
                  value={fields.year}
                  onChange={(event) => change({ year: event.target.value })}
                />
              </div>
            )}
          </div>
        </>
      )}
      {showDate && (
        <div className="form-field date-field">
          <label htmlFor={id("date-tried")}>Date tried</label>
          <input
            id={id("date-tried")}
            type="date"
            required
            value={fields.consumedDate}
            onChange={(event) => change({ consumedDate: event.target.value })}
          />
        </div>
      )}
      {!fields.releaseId && !fields.catalogReleaseId && (
        <details className="capture-extras">
          <summary>
            More label details <span>Optional</span>
          </summary>
          <div className="form-field">
            <label htmlFor={id("producer")}>Producer</label>
            <input
              id={id("producer")}
              maxLength={200}
              value={fields.producer}
              onChange={(event) => change({ producer: event.target.value })}
            />
          </div>
          <div className="form-field">
            <label htmlFor={id("edition")}>Edition or release</label>
            <input
              id={id("edition")}
              maxLength={120}
              value={fields.edition}
              onChange={(event) => change({ edition: event.target.value })}
              placeholder="For example, Reserve"
            />
          </div>
        </details>
      )}
    </>
  );
}
