import { readFile } from "node:fs/promises";
import { parseEnv } from "node:util";

export default async function localOnly() {
  try {
    const web = parseEnv(await readFile(".env.local", "utf8"));
    const api = parseEnv(await readFile("../api/.env", "utf8"));
    const required = {
      SUPABASE_URL: "http://127.0.0.1:54321",
      WINE_JOURNAL_SITE_URL: "http://localhost:3000",
      WINE_JOURNAL_API_URL: "http://127.0.0.1:8000",
      WINE_JOURNAL_AUTH_ISSUER: "http://127.0.0.1:54321/auth/v1",
    };
    for (const [name, value] of Object.entries(required)) {
      if ((process.env[name] ?? web[name] ?? api[name]) !== value) throw new Error();
    }
    const database = new URL(
      process.env.WINE_JOURNAL_DATABASE_URL ?? api.WINE_JOURNAL_DATABASE_URL ?? "",
    );
    if (
      !["localhost", "127.0.0.1", "[::1]"].includes(database.hostname) ||
      database.port !== "54322"
    )
      throw new Error();
    if ((process.env.WINE_JOURNAL_OAUTH_PROVIDERS ?? web.WINE_JOURNAL_OAUTH_PROVIDERS ?? "") !== "")
      throw new Error();
  } catch {
    throw new Error(
      "Browser tests require the generated local-only configuration with social providers disabled. Hosted environments are refused; values withheld.",
    );
  }
}
