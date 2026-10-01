import { useId } from "react";
import type { EditDraft } from "./edit-draft";

export function EntryFields({
  draft,
  busy,
  change,
}: {
  draft: EditDraft;
  busy: boolean;
  change: (next: EditDraft) => void;
}) {
  const id = useId();
  return (
    <fieldset disabled={busy}>
      <legend>Edit this drinking entry</legend>
      <div className="capture-columns">
        <div className="form-field">
          <label htmlFor={`${id}-date`}>Date tried</label>
          <input
            id={`${id}-date`}
            type="date"
            required
            value={draft.consumedDate}
            onChange={(event) => change({ ...draft, consumedDate: event.target.value })}
          />
        </div>
        <div className="form-field">
          <label htmlFor={`${id}-time`}>Local time</label>
          <input
            id={`${id}-time`}
            type="time"
            step={60}
            value={draft.localTime}
            aria-describedby={`${id}-time-help`}
            onChange={(event) =>
              change({
                ...draft,
                localTime: event.target.value,
                timezone: event.target.value
                  ? draft.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
                  : "",
              })
            }
          />
          <p id={`${id}-time-help`}>Optional. Leave blank if you don’t remember.</p>
        </div>
      </div>
      {draft.localTime && (
        <div className="form-field">
          <label htmlFor={`${id}-zone`}>Timezone</label>
          <input
            id={`${id}-zone`}
            required
            maxLength={100}
            value={draft.timezone}
            list={`${id}-zones`}
            aria-describedby={`${id}-zone-help`}
            onChange={(event) => change({ ...draft, timezone: event.target.value })}
          />
          <datalist id={`${id}-zones`}>
            <option value="UTC" />
            {Intl.supportedValuesOf("timeZone").map((zone) => (
              <option key={zone} value={zone} />
            ))}
          </datalist>
          <p id={`${id}-zone-help`}>
            Starts with this device’s timezone. Choose where you drank; the date stays as entered.
          </p>
        </div>
      )}
      <div className="form-field">
        <label htmlFor={`${id}-place`}>Location</label>
        <input
          id={`${id}-place`}
          maxLength={200}
          value={draft.locationLabel}
          placeholder="Restaurant, winery, or a friend’s house"
          onChange={(event) => change({ ...draft, locationLabel: event.target.value })}
        />
      </div>
      <div className="form-field">
        <label htmlFor={`${id}-notes`}>Notes</label>
        <textarea
          id={`${id}-notes`}
          rows={5}
          maxLength={10000}
          value={draft.notes}
          placeholder="What stood out? A flavor, a pairing, or a memory…"
          onChange={(event) => change({ ...draft, notes: event.target.value })}
        />
      </div>
    </fieldset>
  );
}
