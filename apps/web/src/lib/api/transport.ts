import createClient from "openapi-fetch";
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

  return {
    clear() {
      generation++;
      current = undefined;
    },
    async account(): Promise<Account> {
      let rejected: string | undefined;
      for (let attempt = 0; attempt < 2; attempt++) {
        const credentials = await session(rejected);
        const api = createClient<paths>({
          baseUrl: credentials.apiUrl,
          headers: { Authorization: `Bearer ${credentials.accessToken}` },
          credentials: "omit",
          cache: "no-store",
        });
        const options = { signal: AbortSignal.timeout(10000) };
        let result = await api.GET("/api/v1/me", options);
        if (result.response.status === 404)
          result = await api.POST("/api/v1/me", { ...options, body: {} });
        if (result.data) return { ...result.data, email: credentials.email };
        if (result.response.status === 401 && attempt === 0) {
          rejected = credentials.accessToken;
          continue;
        }
        throw new RequestFailure(
          result.response.status,
          result.response.status === 403
            ? "This account is unavailable. You can sign out and use another account."
            : "We couldn't open your journal. Please try again.",
        );
      }
      throw new RequestFailure(401, "Your session has ended.");
    },
  };
}
