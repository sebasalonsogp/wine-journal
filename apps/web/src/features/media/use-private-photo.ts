"use client";

import { useEffect, useState } from "react";
import type { PhotoApi } from "./photo-upload";

/** Only processed thumbnails enter the DOM; signed capabilities stay out of it. */
export function usePrivatePhoto(api: PhotoApi, assetId: string | null, attempt = 0) {
  const [result, setResult] = useState<{ assetId: string; url: string; failed: boolean } | null>(
    null,
  );
  useEffect(() => {
    if (!assetId) return;
    const controller = new AbortController();
    let url = "";
    void Promise.resolve().then(async () => {
      try {
        const view = await api.call((client, timeout) =>
          client.POST("/api/v1/media/{asset_id}/view", {
            params: { path: { asset_id: assetId } },
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
        setResult({ assetId, url, failed: false });
      } catch {
        if (!controller.signal.aborted) setResult({ assetId, url: "", failed: true });
      }
    });
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [api, assetId, attempt]);
  return result?.assetId === assetId ? result : null;
}
