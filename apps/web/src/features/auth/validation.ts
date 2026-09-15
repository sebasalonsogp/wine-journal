export const providers = ["google", "apple", "facebook"] as const;
export type AuthProvider = (typeof providers)[number];

const destinations = new Set(["/my-wines", "/occasions", "/profile", "/browse", "/guides"]);

export function returnPath(value: unknown): string {
  return typeof value === "string" && destinations.has(value) ? value : "/my-wines";
}

export function enabledProviders(value: string): AuthProvider[] {
  return providers.filter((provider) =>
    value
      .split(",")
      .map((part) => part.trim())
      .includes(provider),
  );
}

export class AuthFailure extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function checkOrigin(request: Request, siteOrigin: string): void {
  if (
    request.headers.get("origin") !== siteOrigin ||
    request.headers.get("sec-fetch-site") === "cross-site"
  ) {
    throw new AuthFailure(
      403,
      "This request could not be verified. Reload the page and try again.",
    );
  }
}

export async function readForm(
  request: Request,
  siteOrigin: string,
): Promise<Record<string, unknown>> {
  checkOrigin(request, siteOrigin);
  if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") {
    throw new AuthFailure(415, "Please submit the sign-in form again.");
  }
  const reader = request.body?.getReader();
  if (!reader) throw new AuthFailure(400, "Please complete the sign-in form.");
  const parts: Uint8Array[] = [];
  let length = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.length;
      if (length > 4096) {
        await reader.cancel();
        throw new AuthFailure(413, "The sign-in form is too large.");
      }
      parts.push(value);
    }
    const bytes = new Uint8Array(length);
    let offset = 0;
    for (const part of parts) {
      bytes.set(part, offset);
      offset += part.length;
    }
    const body: unknown = JSON.parse(new TextDecoder().decode(bytes));
    if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error();
    return body as Record<string, unknown>;
  } catch (error) {
    if (error instanceof AuthFailure) throw error;
    throw new AuthFailure(400, "Please complete the sign-in form again.");
  } finally {
    reader.releaseLock();
  }
}

export function emailAddress(value: unknown): string {
  if (
    typeof value !== "string" ||
    value.length > 254 ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
  ) {
    throw new AuthFailure(400, "Enter a valid email address.");
  }
  return value.trim();
}

export function verificationCode(value: unknown): string {
  if (typeof value !== "string" || !/^\d{6}$/.test(value)) {
    throw new AuthFailure(400, "Enter the six-digit code from your email.");
  }
  return value;
}
