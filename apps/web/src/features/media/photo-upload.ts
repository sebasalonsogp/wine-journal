import type { createTransport } from "@/lib/api/transport";
import type { components } from "@/lib/api/schema";
import { RequestFailure } from "@/lib/session/http";

export type PhotoApi = ReturnType<typeof createTransport>;
export type EntryPhoto = components["schemas"]["EntryPhotoResponse"];
export type UploadIdentity = { operationKey: string; assetId?: string };
export const PHOTO_ACCEPT = "image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif";
export const MAX_PHOTO_BYTES = 20 * 1024 * 1024;

export function photoType(file: Pick<File, "type" | "name" | "size">): string {
  const type =
    file.type.toLowerCase() ||
    (/\.hei[cf]$/i.test(file.name)
      ? file.name.toLowerCase().endsWith(".heic")
        ? "image/heic"
        : "image/heif"
      : "");
  if (!["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"].includes(type))
    throw new Error("Choose a JPEG, PNG, WebP or HEIC photo. Videos come later.");
  if (file.size < 1 || file.size > MAX_PHOTO_BYTES)
    throw new Error("Choose a photo smaller than 20 MB.");
  return type;
}

export function photoFailure(failure: unknown): string {
  if (failure instanceof RequestFailure) {
    const messages: Record<string, string> = {
      MEDIA_QUOTA_EXCEEDED:
        "Photo storage is full for this preview. Your entry is saved; keep this photo on your device.",
      UPLOAD_LIMIT: "Two photos are already being processed. Wait for them to finish, then retry.",
      ENTRY_PHOTO_LIMIT: "This entry already has 12 photos. Remove one before adding another.",
      PHOTO_REMOVED: "This photo was removed elsewhere. Remove this selection to continue.",
      PHOTO_CONFLICT: "This photo changed elsewhere. Reload photos before editing or removing it.",
      MEDIA_UNAVAILABLE: "Photo uploads are unavailable. Your entry can still be saved.",
      UPLOAD_MISMATCH: "This file was rejected. Remove it and choose another photo.",
      UPLOAD_MISSING:
        "The photo upload was interrupted. Check your connection and retry; your entry is saved.",
      UPLOAD_EXPIRED: "The upload link expired. Retry to continue with a fresh link.",
    };
    return messages[failure.code ?? ""] ?? failure.message;
  }
  return "The photo could not finish. Check your connection and retry; your entry is kept.";
}

export function attachPhoto(api: PhotoApi, entryId: string, assetId: string, signal: AbortSignal) {
  signal.throwIfAborted();
  return api.call((client, timeout) =>
    client.PUT("/api/v1/entries/{entry_id}/photos/{asset_id}", {
      params: { path: { entry_id: entryId, asset_id: assetId } },
      body: {},
      signal: AbortSignal.any([signal, timeout]),
    }),
  );
}

/** Keep identity across uncertain responses. Never upsert or create another entry. */
export async function uploadPhoto(
  api: PhotoApi,
  entryId: string,
  file: File,
  identity: UploadIdentity,
  signal: AbortSignal,
  reserved: (assetId: string) => void,
): Promise<void> {
  const contentType = photoType(file) as components["schemas"]["UploadRequest"]["contentType"];
  const complete = () =>
    api.call((client, timeout) =>
      client.POST("/api/v1/media/{asset_id}/complete", {
        params: { path: { asset_id: identity.assetId! } },
        body: {},
        signal: AbortSignal.any([signal, timeout]),
      }),
    );
  signal.throwIfAborted();
  if (identity.assetId) {
    await attachPhoto(api, entryId, identity.assetId, signal);
    // The bytes or completion may have arrived even when the previous response was lost.
    try {
      await complete();
      return;
    } catch (failure) {
      if (
        !(failure instanceof RequestFailure) ||
        !["UPLOAD_MISSING", "UPLOAD_EXPIRED"].includes(failure.code ?? "")
      )
        throw failure;
    }
  }
  signal.throwIfAborted();
  const grant = await api.call((client, timeout) =>
    client.POST("/api/v1/media/uploads", {
      params: { header: { "Idempotency-Key": identity.operationKey } },
      body: { contentType, sizeBytes: file.size },
      signal: AbortSignal.any([signal, timeout]),
    }),
  );
  identity.assetId = grant.assetId;
  reserved(grant.assetId);
  await attachPhoto(api, entryId, grant.assetId, signal);
  signal.throwIfAborted();
  // The capability carries authorization. Never send the journal bearer token to Storage.
  try {
    await fetch(grant.uploadUrl, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": grant.contentType },
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
      signal: AbortSignal.any([signal, AbortSignal.timeout(90000)]),
    });
  } catch {
    signal.throwIfAborted();
    // Completion checks authoritative stored bytes, including an uncertain successful PUT.
  }
  signal.throwIfAborted();
  await complete();
}
