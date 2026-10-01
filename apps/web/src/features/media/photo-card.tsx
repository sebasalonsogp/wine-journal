"use client";

import { useEffect, useId, useRef, useState } from "react";
import { photoFailure, type EntryPhoto, type PhotoApi } from "./photo-upload";

export function PhotoCard({
  photo,
  api,
  refresh,
}: {
  photo: EntryPhoto;
  api: PhotoApi;
  refresh: () => void;
}) {
  const id = useId();
  const [image, setImage] = useState("");
  const [imageError, setImageError] = useState(false);
  const [viewAttempt, setViewAttempt] = useState(0);
  const [draft, setDraft] = useState<{ caption: string; version: number } | null>(null);
  const caption = draft?.caption ?? photo.caption ?? "";
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  const lifetime = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    lifetime.current = controller;
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (photo.state !== "READY") return;
    const controller = new AbortController();
    let url = "";
    void Promise.resolve().then(async () => {
      try {
        setImageError(false);
        const view = await api.call((client, timeout) =>
          client.POST("/api/v1/media/{asset_id}/view", {
            params: { path: { asset_id: photo.assetId } },
            body: { variant: "thumbnail" },
            signal: AbortSignal.any([controller.signal, timeout]),
          }),
        );
        controller.signal.throwIfAborted();
        const response = await fetch(view.viewUrl, {
          cache: "no-store",
          credentials: "omit",
          referrerPolicy: "no-referrer",
          redirect: "error",
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
        });
        if (!response.ok || !response.headers.get("content-type")?.startsWith("image/webp"))
          throw new Error();
        const blob = await response.blob();
        if (blob.size > 512 * 1024 || !blob.size) throw new Error();
        controller.signal.throwIfAborted();
        url = URL.createObjectURL(blob);
        setImage(url);
      } catch {
        if (!controller.signal.aborted) setImageError(true);
      }
    });
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [api, photo.assetId, photo.state, viewAttempt]);

  async function mutate(remove: boolean) {
    if (submitting.current) return;
    if (
      remove &&
      !window.confirm("Remove this photo from this entry? Other entries using it will keep it.")
    )
      return;
    submitting.current = true;
    setBusy(true);
    setError("");
    const signal = lifetime.current!.signal;
    try {
      const path = { entry_id: photo.entryId, asset_id: photo.assetId };
      if (remove)
        await api.call((client, timeout) =>
          client.DELETE("/api/v1/entries/{entry_id}/photos/{asset_id}", {
            params: { path, query: { version: photo.version } },
            signal: AbortSignal.any([signal, timeout]),
          }),
        );
      else
        await api.call((client, timeout) =>
          client.PATCH("/api/v1/entries/{entry_id}/photos/{asset_id}", {
            params: { path },
            body: { version: draft?.version ?? photo.version, caption: caption.trim() || null },
            signal: AbortSignal.any([signal, timeout]),
          }),
        );
      if (!signal.aborted) {
        setDraft(null);
        refresh();
      }
    } catch (failure) {
      if (!signal.aborted) setError(photoFailure(failure));
    } finally {
      submitting.current = false;
      if (!signal.aborted) setBusy(false);
    }
  }

  return (
    <li className="photo-card" data-testid="entry-photo">
      <div className="photo-frame">
        {image && photo.state === "READY" ? (
          // Temporary blob URLs keep signed capabilities out of the DOM and image optimizer.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image}
            alt={photo.caption || "Photo from this drinking entry"}
            width={480}
            height={480}
          />
        ) : (
          <p role="status">
            {photo.state === "READY"
              ? imageError
                ? "Photo could not load."
                : "Loading photo…"
              : photo.state === "FAILED"
                ? "This photo couldn’t be processed. Remove it and choose another."
                : photo.state === "PROCESSING"
                  ? "Preparing your photo…"
                  : "Upload unfinished. Retry in the original tab, or remove and choose the photo again."}
          </p>
        )}
      </div>
      {imageError && (
        <button
          type="button"
          className="text-button"
          onClick={() => setViewAttempt((value) => value + 1)}
        >
          Retry image
        </button>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void mutate(false);
        }}
      >
        <div className="form-field">
          <label htmlFor={`${id}-caption`}>
            Photo caption <span>optional</span>
          </label>
          <textarea
            id={`${id}-caption`}
            rows={2}
            maxLength={500}
            value={caption}
            disabled={busy}
            onChange={(event) =>
              setDraft({ caption: event.target.value, version: draft?.version ?? photo.version })
            }
            placeholder="A detail worth remembering"
          />
        </div>
        <div className="photo-actions">
          <button className="text-button" disabled={busy || caption === (photo.caption ?? "")}>
            {busy ? "Saving…" : "Save caption"}
          </button>
          <button
            type="button"
            className="text-button"
            disabled={busy}
            onClick={() => void mutate(true)}
          >
            Remove photo
          </button>
          {draft && (
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => {
                setDraft(null);
                setError("");
                refresh();
              }}
            >
              Use saved caption
            </button>
          )}
        </div>
      </form>
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
    </li>
  );
}
