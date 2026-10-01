"use client";

import { usePrivatePhoto } from "./use-private-photo";
import { BottlePlaceholder } from "@/features/my-wines/wine-display";
import type { PhotoApi } from "./photo-upload";

export function BottleCover({
  api,
  assetId,
  name,
}: {
  api: PhotoApi;
  assetId?: string | null;
  name: string;
}) {
  const photo = usePrivatePhoto(api, assetId ?? null);
  if (!photo?.url) return <BottlePlaceholder />;
  return (
    <div className="bottle-placeholder bottle-cover">
      {/* Only processed private thumbnail blobs are rendered. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={photo.url} alt={`Personal bottle cover for ${name}`} width={480} height={480} />
    </div>
  );
}
