"use client";

import { useEffect, useRef, useState } from "react";
import { RequestFailure } from "@/lib/session/http";
import {
  attachPhoto,
  photoFailure,
  uploadPhoto,
  type PhotoApi,
  type UploadIdentity,
} from "./photo-upload";

export type SelectedPhoto = { key: string; file: File; assetId?: string };

export function PhotoSelection({
  photo,
  entryId,
  api,
  onAsset,
  onDone,
}: {
  photo: SelectedPhoto;
  entryId?: string;
  api: PhotoApi;
  onAsset: (key: string, assetId: string) => void;
  onDone: (key: string) => void;
}) {
  const identity = useRef<UploadIdentity>({ operationKey: photo.key });
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<"queued" | "uploading" | "error">("queued");
  const [error, setError] = useState("");
  const [removing, setRemoving] = useState(false);
  const removingRef = useRef(false);
  const lifetime = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    lifetime.current = controller;
    if (entryId)
      void Promise.resolve().then(async () => {
        if (controller.signal.aborted) return;
        setState("uploading");
        setError("");
        try {
          await uploadPhoto(
            api,
            entryId,
            photo.file,
            identity.current,
            controller.signal,
            (assetId) => {
              if (!controller.signal.aborted) onAsset(photo.key, assetId);
            },
          );
          if (!controller.signal.aborted) onDone(photo.key);
        } catch (failure) {
          if (!controller.signal.aborted) {
            setState("error");
            setError(photoFailure(failure));
          }
        }
      });
    return () => controller.abort();
  }, [api, entryId, photo.file, photo.key, attempt, onAsset, onDone]);

  async function remove() {
    if (removingRef.current || state === "uploading") return;
    removingRef.current = true;
    setRemoving(true);
    setError("");
    const signal = lifetime.current!.signal;
    try {
      if (entryId && identity.current.assetId) {
        // Resolve a possibly lost attach response before removing its reference.
        try {
          const attached = await attachPhoto(api, entryId, identity.current.assetId, signal);
          await api.call((client, timeout) =>
            client.DELETE("/api/v1/entries/{entry_id}/photos/{asset_id}", {
              params: {
                path: { entry_id: entryId, asset_id: attached.assetId },
                query: { version: attached.version },
              },
              signal: AbortSignal.any([signal, timeout]),
            }),
          );
        } catch (failure) {
          if (
            !(failure instanceof RequestFailure) ||
            !["PHOTO_REMOVED", "ENTRY_PHOTO_LIMIT", "ENTRY_NOT_FOUND", "UPLOAD_NOT_FOUND"].includes(
              failure.code ?? "",
            )
          )
            throw failure;
        }
      }
      if (!signal.aborted) onDone(photo.key);
    } catch (failure) {
      if (!signal.aborted) setError(photoFailure(failure));
    } finally {
      removingRef.current = false;
      if (!signal.aborted) setRemoving(false);
    }
  }

  return (
    <li className="photo-selection" data-testid="photo-selection">
      <p className="photo-filename">{photo.file.name}</p>
      <p role="status">
        {state === "uploading"
          ? "Uploading photo…"
          : state === "error"
            ? "Upload needs attention"
            : "Selected — uploads after you save the entry."}
      </p>
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      <div className="photo-actions">
        {state === "error" && (
          <button
            type="button"
            className="button button-secondary"
            disabled={removing}
            onClick={() => setAttempt((value) => value + 1)}
          >
            Retry photo
          </button>
        )}
        <button
          type="button"
          className="text-button"
          disabled={state === "uploading" || removing}
          onClick={() => void remove()}
        >
          {removing ? "Removing…" : "Remove selection"}
        </button>
      </div>
    </li>
  );
}
