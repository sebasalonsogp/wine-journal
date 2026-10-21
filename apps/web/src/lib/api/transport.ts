import createClient, { type Client } from "openapi-fetch";
import type { paths, components } from "./schema";
import { authRequest, RequestFailure } from "@/lib/session/http";

type Session = {
  accessToken: string;
  subject: string;
  email: string | null;
  expiresAt: number;
  apiUrl: string;
};
export type Account = components["schemas"]["AccountResponse"] & { email: string | null };
type Operation<T> = (
  api: Client<paths>,
  signal: AbortSignal,
) => Promise<{ data?: T; error?: unknown; response: Response }>;

// One instance per mounted private shell. Tokens stay in memory, never query caches.
export function createTransport() {
  let current: Session | undefined;
  let pending: Promise<Session> | undefined;
  let generation = 0;

  async function session(rejectedToken?: string): Promise<Session> {
    if (
      current &&
      current.expiresAt > Date.now() / 1000 + 30 &&
      current.accessToken !== rejectedToken
    )
      return current;
    if (!pending) {
      const started = generation;
      pending = authRequest<Session>("/auth/session", { refresh: Boolean(rejectedToken) })
        .then((value) => {
          if (started !== generation) throw new RequestFailure(401, "Your session has ended.");
          current = value;
          return value;
        })
        .finally(() => {
          pending = undefined;
        });
    }
    return pending;
  }

  async function call<T>(operation: Operation<T>): Promise<T> {
    const started = generation;
    let rejected: string | undefined;
    for (let attempt = 0; attempt < 2; attempt++) {
      const credentials = await session(rejected);
      const api = createClient<paths>({
        baseUrl: credentials.apiUrl,
        headers: { Authorization: `Bearer ${credentials.accessToken}` },
        credentials: "omit",
        cache: "no-store",
      });
      let result;
      try {
        result = await operation(api, AbortSignal.timeout(10000));
      } catch {
        throw new RequestFailure(
          503,
          "We couldn't confirm the request. Check your connection and try again.",
        );
      }
      if (started !== generation) throw new RequestFailure(401, "Your session has ended.");
      if (result.data !== undefined) return result.data;
      if (result.response.status === 401 && attempt === 0) {
        rejected = credentials.accessToken;
        continue;
      }
      throw new RequestFailure(
        result.response.status,
        result.response.status === 403
          ? "This account is unavailable. You can sign out and use another account."
          : result.response.status === 404
            ? "This record is unavailable. Return to your journal to choose another."
            : result.response.status === 422
              ? "Check the details, then try again."
              : "We couldn't complete the request. Please try again.",
        publicErrorCode(result.error),
      );
    }
    throw new RequestFailure(401, "Your session has ended.");
  }

  return {
    call,
    clear() {
      generation++;
      current = undefined;
    },
    async account(): Promise<Account> {
      // Recheck the cookie session on focus, including OAuth changes in another tab.
      current = undefined;
      const data = await call(async (api, signal) => {
        const options = { signal };
        let result = await api.GET("/api/v1/me", options);
        if (result.response.status === 404)
          result = await api.POST("/api/v1/me", { ...options, body: {} });
        return result;
      });
      return { ...data, email: (current as Session | undefined)?.email ?? null };
    },
  };
}

function publicErrorCode(value: unknown): string | undefined {
  if (!value || typeof value !== "object" || !("error" in value)) return;
  const error = value.error;
  if (!error || typeof error !== "object" || !("code" in error)) return;
  return typeof error.code === "string" && /^[A-Z_]{1,64}$/.test(error.code)
    ? error.code
    : undefined;
}
