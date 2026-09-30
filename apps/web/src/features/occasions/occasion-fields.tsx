import { useId } from "react";
import type { OccasionDraft } from "./occasion-draft";

export function OccasionFields({
  draft,
  disabled,
  change,
}: {
  draft: OccasionDraft;
  disabled: boolean;
  change: (draft: OccasionDraft) => void;
}) {
  const id = useId();
  return (
    <fieldset disabled={disabled}>
      <legend>Occasion details</legend>
      <div className="form-field">
        <label htmlFor={`${id}-title`}>
          Title <span>optional</span>
        </label>
        <input
          id={`${id}-title`}
          maxLength={200}
          value={draft.title}
          placeholder="Dinner with friends"
          onChange={(event) => change({ ...draft, title: event.target.value })}
          aria-describedby={`${id}-title-help`}
        />
        <p id={`${id}-title-help`}>Leave blank to use the date as the title.</p>
      </div>
      <div className="capture-columns">
        <div className="form-field">
          <label htmlFor={`${id}-date`}>Occasion date</label>
          <input
            id={`${id}-date`}
            type="date"
            required
            value={draft.occasionDate}
            onChange={(event) => change({ ...draft, occasionDate: event.target.value })}
          />
        </div>
        <div className="form-field">
          <label htmlFor={`${id}-time`}>
            Local time <span>optional</span>
          </label>
          <input
            id={`${id}-time`}
            type="time"
            step={60}
            value={draft.localTime}
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
            onChange={(event) => change({ ...draft, timezone: event.target.value })}
            aria-describedby={`${id}-zone-help`}
          />
          <datalist id={`${id}-zones`}>
            <option value="UTC" />
            {Intl.supportedValuesOf("timeZone").map((zone) => (
              <option key={zone} value={zone} />
            ))}
          </datalist>
          <p id={`${id}-zone-help`}>
            Starts with this device’s timezone. Choose where the occasion took place.
          </p>
        </div>
      )}
      <div className="form-field">
        <label htmlFor={`${id}-place`}>
          Location <span>optional</span>
        </label>
        <input
          id={`${id}-place`}
          maxLength={200}
          value={draft.locationLabel}
          placeholder="Restaurant, winery, or a friend’s house"
          onChange={(event) => change({ ...draft, locationLabel: event.target.value })}
        />
      </div>
      <div className="form-field">
        <label htmlFor={`${id}-notes`}>
          Notes <span>optional</span>
        </label>
        <textarea
          id={`${id}-notes`}
          rows={5}
          maxLength={10000}
          value={draft.notes}
          placeholder="Who was there? What would you like to remember?"
          onChange={(event) => change({ ...draft, notes: event.target.value })}
        />
      </div>
    </fieldset>
  );
}
