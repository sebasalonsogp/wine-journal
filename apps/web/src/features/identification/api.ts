import createClient from "openapi-fetch";
import type { components, paths } from "@/lib/api/schema";

export class BarcodeFailure extends Error {
  constructor(
    public status: number,
    public retryAfter = 0,
  ) {
    super(
      status === 422
        ? "Check the numbers beneath the barcode, including any leading zeros."
        : status === 409
          ? "This match has changed. Look up the barcode again before choosing a wine."
          : status === 429
            ? "Too many lookups. Please wait before trying again."
            : "We couldn’t look up this bottle. Check your connection and try again.",
    );
  }
}

async function read<T>(operation: () => Promise<{ data?: T; response: Response }>): Promise<T> {
  try {
    const { data, response } = await operation();
    if (response.ok && data !== undefined) return data;
    const seconds = Number(response.headers.get("Retry-After"));
    const retry = response.status === 429 || response.status === 503;
    throw new BarcodeFailure(
      response.status,
      retry ? (Number.isFinite(seconds) && seconds > 0 ? Math.min(300, Math.ceil(seconds)) : 5) : 0,
    );
  } catch (error) {
    if (error instanceof BarcodeFailure) throw error;
    throw new BarcodeFailure(503);
  }
}

export function barcodeApi(origin: string) {
  // The server supplies only the validated public origin. No session is requested.
  const api = createClient<paths>({
    baseUrl: origin,
    credentials: "omit",
    cache: "no-store",
    redirect: "error",
  });
  const bounded = (signal: AbortSignal) => AbortSignal.any([signal, AbortSignal.timeout(10000)]);
  return {
    lookup: (gtin: string, signal: AbortSignal) =>
      read(() =>
        api.POST("/api/v1/identification/barcode-lookups", {
          body: { gtin },
          signal: bounded(signal),
        }),
      ),
    confirm: (body: components["schemas"]["BarcodeConfirmation"], signal: AbortSignal) =>
      read(() =>
        api.POST("/api/v1/identification/barcode-confirmations", { body, signal: bounded(signal) }),
      ),
  };
}
