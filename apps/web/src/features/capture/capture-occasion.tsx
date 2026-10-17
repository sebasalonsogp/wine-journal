"use client";

import Link from "next/link";
import { useState } from "react";
import { type createTransport } from "@/lib/api/transport";
import { newOccasionDraft } from "@/features/occasions/occasion-draft";
import { OccasionFields } from "@/features/occasions/occasion-fields";
import { ExistingOccasions } from "@/features/occasions/occasion-select";
import type { Fields } from "./draft";

export function CaptureOccasion({
  fields,
  change,
  owner,
  api,
}: {
  fields: Fields;
  change: (values: Partial<Fields>) => void;
  owner: string | null;
  api: ReturnType<typeof createTransport>;
}) {
  const [choosing, setChoosing] = useState(Boolean(fields.occasionId));
  return (
    <section className="capture-occasion" aria-labelledby="capture-occasion-title">
      <h2 id="capture-occasion-title">
        An occasion <span>optional</span>
      </h2>
      <p>Keep this glass on its own, or remember it as part of a bigger moment.</p>
      {fields.newOccasion ? (
        <>
          <OccasionFields
            draft={fields.newOccasion}
            disabled={false}
            change={(newOccasion) => change({ newOccasion })}
          />
          <button
            type="button"
            className="text-button"
            onClick={() => change({ newOccasion: null })}
          >
            Cancel new occasion
          </button>
          <p className="form-footnote">
            The new occasion and this wine entry will be saved together.
          </p>
        </>
      ) : choosing && owner ? (
        <>
          <ExistingOccasions
            key={owner}
            id="existing-occasion"
            api={api}
            selected={fields.occasionId}
            select={(occasionId) => change({ occasionId })}
          />
          <button
            type="button"
            className="text-button"
            onClick={() => {
              change({ occasionId: null });
              setChoosing(false);
            }}
          >
            Keep without an occasion
          </button>
        </>
      ) : (
        <div className="capture-actions">
          {owner ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={() => setChoosing(true)}
            >
              Choose existing occasion
            </button>
          ) : (
            <Link href="/auth/sign-in?next=%2Fcapture">Sign in to choose an occasion</Link>
          )}
          <button
            type="button"
            className="button button-secondary"
            onClick={() => {
              change({
                occasionId: null,
                newOccasion: { ...newOccasionDraft(), occasionDate: fields.consumedDate },
              });
              setChoosing(false);
            }}
          >
            Create new occasion
          </button>
        </div>
      )}
    </section>
  );
}
