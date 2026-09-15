import "server-only";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { authConfig } from "./config";

export const authCookie = "wine-journal-session";

export async function serverAuth() {
  const config = authConfig();
  const store = await cookies();
  return createServerClient(config.supabase, config.key, {
    cookieOptions: {
      name: authCookie,
      httpOnly: true,
      secure: config.secure,
      sameSite: "lax",
      path: "/",
    },
    cookies: {
      getAll: () => store.getAll(),
      setAll: (values) => {
        for (const { name, value, options } of values) {
          store.set(name, value, {
            ...options,
            httpOnly: true,
            secure: config.secure,
            sameSite: "lax",
            path: "/",
          });
        }
      },
    },
    global: {
      fetch: (input, init) =>
        fetch(input, {
          ...init,
          cache: "no-store",
          signal: AbortSignal.any([
            AbortSignal.timeout(8000),
            ...(init?.signal ? [init.signal] : []),
          ]),
        }),
    },
  });
}

export async function clearAuthCookies() {
  const store = await cookies();
  for (const { name } of store.getAll()) {
    if (
      name === authCookie ||
      name.startsWith(authCookie + ".") ||
      name.startsWith(authCookie + "-")
    )
      store.delete(name);
  }
  store.delete("wine-journal-return");
}
