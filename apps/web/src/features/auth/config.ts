import "server-only";
import { enabledProviders } from "./validation";

function origin(value: string | undefined): string {
  if (!value) throw new Error("Web authentication configuration is incomplete.");
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("Invalid web authentication origin configuration.");
  }
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/" ||
    (url.protocol !== "https:" && !(local && url.protocol === "http:"))
  ) {
    throw new Error("Invalid web authentication origin configuration.");
  }
  return url.origin;
}

export function authConfig() {
  const key = process.env.SUPABASE_PUBLISHABLE_KEY;
  // This web boundary needs only a publishable key, never a service-role JWT.
  if (!key?.startsWith("sb_publishable_")) throw new Error("Configure a Supabase publishable key.");
  const site = origin(process.env.WINE_JOURNAL_SITE_URL);
  return {
    supabase: origin(process.env.SUPABASE_URL),
    key,
    site,
    api: origin(process.env.WINE_JOURNAL_API_URL),
    secure: site.startsWith("https:"),
    providers: enabledProviders(process.env.WINE_JOURNAL_OAUTH_PROVIDERS ?? ""),
  };
}
