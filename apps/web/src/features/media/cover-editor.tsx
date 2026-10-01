"use client";

import { useEffect, useId, useRef, useState } from "react";
import { privateResetEvent } from "@/lib/session/private-drafts";
import { RequestFailure } from "@/lib/session/http";
import { BottleCover } from "./bottle-cover";
import { usePendingImages } from "./use-pending-images";
import {
  PHOTO_ACCEPT,
  photoFailure,
  photoType,
  uploadAsset,
  type PhotoApi,
  type UploadIdentity,
} from "./photo-upload";

type Cover = { assetId: string | null; version: number };
type Selection = { file: File; identity: UploadIdentity; version?: number };

export function CoverEditor({
  api,
  wineId,
  onSelectionChange,
  onSaved,
}: {
  api: PhotoApi;
  wineId?: string;
  onSelectionChange?: (count: number) => void;
  onSaved?: () => void;
}) {
  const id = useId();
  const [cover, setCover] = useState<Cover | null>(null);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [reload, setReload] = useState(0);
  const [ended, setEnded] = useState(false);
  const [conflict, setConflict] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const selectedRef = useRef(selected);
  const savedCallback = useRef(onSaved);
  useEffect(() => {
    selectedRef.current = selected;
    savedCallback.current = onSaved;
  }, [selected, onSaved]);
  usePendingImages(Boolean(selected));

  useEffect(() => {
    onSelectionChange?.(selected ? 1 : 0);
  }, [selected, onSelectionChange]);
  useEffect(() => {
    const reset = () => {
      controller.current?.abort();
      setEnded(true);
      setSelected(null);
      setCover(null);
    };
    window.addEventListener(privateResetEvent, reset);
    return () => {
      controller.current?.abort();
      window.removeEventListener(privateResetEvent, reset);
    };
  }, []);
  useEffect(() => {
    if (!wineId || ended) return;
    const abort = new AbortController();
    void api
      .call((client, timeout) =>
        client.GET("/api/v1/me/wines/{wine_id}", {
          params: { path: { wine_id: wineId } },
          signal: AbortSignal.any([abort.signal, timeout]),
        }),
      )
      .then((wine) => {
        if (abort.signal.aborted) return;
        const next = { assetId: wine.coverAssetId ?? null, version: wine.coverVersion ?? 0 };
        setCover(next);
        setError("");
        // Reviewing a conflict updates the expected version, but never starts another write.
        if (selectedRef.current && (reload || selectedRef.current.version === undefined))
          selectedRef.current.version = next.version;
        if (reload) {
          setConflict(false);
          setNotice("Current cover loaded. Retry to use your selected image, or discard it.");
        }
      })
      .catch((failure) => {
        if (!abort.signal.aborted) setError(photoFailure(failure));
      });
    return () => abort.abort();
  }, [api, wineId, reload, ended]);

  const ready = Boolean(cover);
  const selectionKey = selected?.identity.operationKey;
  useEffect(() => {
    if (!wineId || !ready || !selectionKey || ended) return;
    const selection = selectedRef.current!;
    const abort = new AbortController();
    controller.current = abort;
    void Promise.resolve().then(async () => {
      if (abort.signal.aborted) return;
      setBusy(true);
      setError("");
      setNotice("Uploading your bottle cover…");
      try {
        await uploadAsset(api, selection.file, selection.identity, abort.signal);
        setNotice("Preparing your bottle cover… Your current cover stays until this one is ready.");
        for (let poll = 0; ; poll++) {
          const status = await api.call((client, timeout) =>
            client.GET("/api/v1/media/{asset_id}", {
              params: { path: { asset_id: selection.identity.assetId! } },
              signal: AbortSignal.any([abort.signal, timeout]),
            }),
          );
          abort.signal.throwIfAborted();
          if (status.state === "READY") break;
          if (status.state === "FAILED")
            throw new Error("This image couldn’t be processed. Discard it and choose another.");
          if (poll >= 59)
            throw new Error("This image is still processing. Retry shortly to check again.");
          await new Promise<void>((resolve, reject) => {
            const cancel = () => {
              clearTimeout(timer);
              reject(new DOMException("Aborted", "AbortError"));
            };
            const timer = setTimeout(() => {
              abort.signal.removeEventListener("abort", cancel);
              resolve();
            }, 5000);
            abort.signal.addEventListener("abort", cancel, { once: true });
          });
        }
        const result = await api.call((client, timeout) =>
          client.PUT("/api/v1/me/wines/{wine_id}/cover", {
            params: { path: { wine_id: wineId } },
            body: { assetId: selection.identity.assetId!, version: selection.version! },
            signal: AbortSignal.any([abort.signal, timeout]),
          }),
        );
        if (abort.signal.aborted) return;
        setCover(result);
        setSelected(null);
        setNotice("Bottle cover saved.");
        savedCallback.current?.();
      } catch (failure) {
        if (!abort.signal.aborted) {
          setNotice("");
          const stale = failure instanceof RequestFailure && failure.code === "COVER_CONFLICT";
          setConflict(stale);
          setError(
            stale
              ? "Your cover changed in another tab. Review the current cover before replacing it."
              : failure instanceof RequestFailure
                ? photoFailure(failure)
                : failure instanceof Error
                  ? failure.message
                  : "The cover could not finish. Retry to continue.",
          );
        }
      } finally {
        if (!abort.signal.aborted) setBusy(false);
      }
    });
    return () => abort.abort();
  }, [api, wineId, ready, selectionKey, attempt, ended]);

  async function remove() {
    if (
      !wineId ||
      !cover ||
      busy ||
      !window.confirm(
        "Remove your personal bottle cover? Your drinking entries and memories will stay.",
      )
    )
      return;
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    try {
      const result = await api.call((client, timeout) =>
        client.PUT("/api/v1/me/wines/{wine_id}/cover", {
          params: { path: { wine_id: wineId } },
          body: { assetId: null, version: cover.version },
          signal: AbortSignal.any([abort.signal, timeout]),
        }),
      );
      if (!abort.signal.aborted) {
        setCover(result);
        setNotice("Personal cover removed.");
        savedCallback.current?.();
      }
    } catch {
      if (!abort.signal.aborted) {
        setError("The cover could not be removed. Reload the current cover and retry.");
      }
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }

  if (ended) return null;
  return (
    <section className="cover-editor" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>
        Bottle cover <span className="optional-label">optional</span>
      </h2>
      <p className="form-footnote">
        Your bottle image across this wine’s entries. It stays separate from your memories.
      </p>
      <div className="cover-editor-body">
        <BottleCover api={api} assetId={cover?.assetId} name="this wine" />
        <div className="cover-controls">
          <div className="form-field photo-picker">
            <label htmlFor={`${id}-file`}>
              {cover?.assetId ? "Replace bottle cover" : "Choose bottle cover"}
            </label>
            <input
              id={`${id}-file`}
              type="file"
              accept={PHOTO_ACCEPT}
              disabled={busy || Boolean(selected) || Boolean(wineId && !cover)}
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (!file) return;
                try {
                  photoType(file);
                  setError("");
                  setNotice(wineId ? "" : "Selected — uploads after you save the entry.");
                  setConflict(false);
                  setSelected({
                    file,
                    identity: { operationKey: crypto.randomUUID() },
                    version: cover?.version,
                  });
                } catch (failure) {
                  setError(failure instanceof Error ? failure.message : "Choose another photo.");
                }
              }}
            />
          </div>
          <p className="form-footnote">
            JPEG, PNG, WebP or HEIC · up to 20 MB. A preview appears after processing.
          </p>
          {selected && <p className="photo-filename">{selected.file.name}</p>}
          {notice && <p role="status">{notice}</p>}
          {error && (
            <p className="form-message" role="alert">
              {error}
            </p>
          )}
          {selected && (
            <p className="form-footnote">
              Keep this page open until the cover is saved. Selected files aren’t kept after a
              reload.
            </p>
          )}
          <div className="photo-actions">
            {selected && wineId && !busy && !conflict && ready && (
              <button
                type="button"
                className="button button-secondary"
                disabled={busy}
                onClick={() => setAttempt((value) => value + 1)}
              >
                Retry cover
              </button>
            )}
            {wineId && !busy && (error || conflict) && (
              <button
                type="button"
                className="text-button"
                onClick={() => setReload((value) => value + 1)}
              >
                Review current cover
              </button>
            )}
            {selected && (
              <button
                type="button"
                className="text-button"
                disabled={busy}
                onClick={() => {
                  setSelected(null);
                  setError("");
                  setNotice("");
                  setConflict(false);
                }}
              >
                Discard cover selection
              </button>
            )}
            {cover?.assetId && !selected && (
              <button
                type="button"
                className="text-button"
                disabled={busy}
                onClick={() => void remove()}
              >
                Remove cover
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
