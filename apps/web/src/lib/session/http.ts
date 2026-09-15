// Shared browser session transport; this module does not depend on product features.
export class RequestFailure extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function authRequest<T>(path: string, body: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new RequestFailure(503, "We couldn't connect. Check your connection and try again.");
  }
  if (!response.ok) {
    // Only our fixed, public auth messages are rendered; no raw provider responses.
    const error = await response.json().catch(() => ({}));
    throw new RequestFailure(
      response.status,
      typeof error.message === "string" ? error.message : "Something went wrong. Please try again.",
    );
  }
  return response.json() as Promise<T>;
}
