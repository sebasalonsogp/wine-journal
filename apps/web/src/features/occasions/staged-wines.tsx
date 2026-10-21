"use client";

import { CaptureFields } from "@/features/capture/capture-fields";
import { entryCount, newWineDraft, type Composer } from "./occasion-composer";

export function StagedWines({
  draft,
  change,
  disabled,
}: {
  draft: Composer;
  change: (draft: Composer) => void;
  disabled: boolean;
}) {
  const child = draft.child;
  const pending = draft.wines.filter((_, index) => index !== draft.editing);
  const count = entryCount(draft.wines);
  return (
    <fieldset className="staged-wines" disabled={disabled}>
      <legend>Wines for this occasion</legend>
      <p className="form-footnote">
        {count} drinking {count === 1 ? "entry" : "entries"} ready · up to 20 per save
      </p>
      {child ? (
        <section className="staged-wine-editor" aria-label="Wine details">
          <CaptureFields
            fields={child.fields}
            change={(values) =>
              change({ ...draft, child: { ...child, fields: { ...child.fields, ...values } } })
            }
          />
          <div className="form-field">
            <label htmlFor="staged-notes">
              Wine notes <span>optional</span>
            </label>
            <textarea
              id="staged-notes"
              rows={3}
              maxLength={10000}
              value={child.fields.notes}
              onChange={(event) =>
                change({
                  ...draft,
                  child: { ...child, fields: { ...child.fields, notes: event.target.value } },
                })
              }
            />
          </div>
          {child.extraEntries.map((entry, index) => (
            <div className="staged-repeat" key={index}>
              <h3>Glass or bottle {index + 2}</h3>
              <div className="form-field">
                <label htmlFor={`repeat-date-${index}`}>Date tried — entry {index + 2}</label>
                <input
                  id={`repeat-date-${index}`}
                  type="date"
                  required
                  value={entry.consumedDate}
                  onChange={(event) =>
                    change({
                      ...draft,
                      child: {
                        ...child,
                        extraEntries: child.extraEntries.map((item, row) =>
                          row === index ? { ...item, consumedDate: event.target.value } : item,
                        ),
                      },
                    })
                  }
                />
              </div>
              <div className="form-field">
                <label htmlFor={`repeat-notes-${index}`}>Notes — entry {index + 2}</label>
                <textarea
                  id={`repeat-notes-${index}`}
                  rows={2}
                  maxLength={10000}
                  value={entry.notes}
                  onChange={(event) =>
                    change({
                      ...draft,
                      child: {
                        ...child,
                        extraEntries: child.extraEntries.map((item, row) =>
                          row === index ? { ...item, notes: event.target.value } : item,
                        ),
                      },
                    })
                  }
                />
              </div>
              <button
                type="button"
                className="text-button"
                onClick={() =>
                  change({
                    ...draft,
                    child: {
                      ...child,
                      extraEntries: child.extraEntries.filter((_, row) => row !== index),
                    },
                  })
                }
              >
                Remove entry {index + 2}
              </button>
            </div>
          ))}
          <button
            type="button"
            className="text-button"
            disabled={entryCount(pending) + 1 + child.extraEntries.length >= 20}
            onClick={() =>
              change({
                ...draft,
                child: {
                  ...child,
                  extraEntries: [
                    ...child.extraEntries,
                    { consumedDate: child.fields.consumedDate, notes: "" },
                  ],
                },
              })
            }
          >
            Add another glass of this wine
          </button>
          <div className="capture-actions">
            <button
              type="button"
              className="button"
              onClick={(event) => {
                if (!event.currentTarget.form?.reportValidity()) return;
                const wines =
                  draft.editing === null
                    ? [...draft.wines, child]
                    : draft.wines.map((wine, index) => (index === draft.editing ? child : wine));
                change({ ...draft, wines, child: null, editing: null });
              }}
            >
              Keep wine in draft
            </button>
            <button
              type="button"
              className="text-button"
              onClick={() => change({ ...draft, child: null, editing: null })}
            >
              Cancel wine
            </button>
          </div>
          <p className="form-footnote">
            Nothing is logged until you save the occasion or its wines.
          </p>
        </section>
      ) : (
        <>
          <ul className="staged-wine-list">
            {draft.wines.map((wine, index) => (
              <li key={index}>
                <h3>{wine.fields.name}</h3>
                <p>
                  {wine.fields.consumedDate} · {1 + wine.extraEntries.length} drinking{" "}
                  {wine.extraEntries.length ? "entries" : "entry"}
                </p>
                <div className="capture-actions">
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => change({ ...draft, child: wine, editing: index })}
                  >
                    Edit {wine.fields.name}
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() =>
                      change({ ...draft, wines: draft.wines.filter((_, row) => row !== index) })
                    }
                  >
                    Remove {wine.fields.name}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="button button-secondary"
            disabled={count >= 20}
            onClick={() =>
              change({ ...draft, child: newWineDraft(draft.occasionDate), editing: null })
            }
          >
            Add a wine
          </button>
        </>
      )}
    </fieldset>
  );
}
