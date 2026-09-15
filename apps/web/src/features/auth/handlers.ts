import "server-only";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { isAuthRetryableFetchError } from "@supabase/supabase-js";
import { authConfig } from "./config";
import { clearAuthCookies, serverAuth } from "./server-client";
import { AuthFailure, emailAddress, readForm, returnPath, verificationCode } from "./validation";

function json(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": "private, no-store", Pragma: "no-cache" },
  });
}

async function handle(action: () => Promise<NextResponse>) {
  try {
    return await action();
  } catch (error) {
    if (error instanceof AuthFailure) return json({ message: error.message }, error.status);
    // Never serialize SDK errors, request bodies, URLs, tokens or email addresses.
    return json({ message: "Sign-in is temporarily unavailable. Please try again shortly." }, 503);
  }
}

export function requestCode(request: Request) {
  return handle(async () => {
    const body = await readForm(request, authConfig().site);
    const email = emailAddress(body.email);
    const auth = await serverAuth();
    const { error } = await auth.auth.signInWithOtp({ email });
    if (error) {
      if (error.status === 429)
        throw new AuthFailure(429, "Please wait a minute before requesting another code.");
      throw new AuthFailure(503, "We couldn't send a code. Please try again shortly.");
    }
    return json({ message: "Check your inbox for a six-digit code." });
  });
}

export function verifyCode(request: Request) {
  return handle(async () => {
    const body = await readForm(request, authConfig().site);
    const auth = await serverAuth();
    const { error } = await auth.auth.verifyOtp({
      email: emailAddress(body.email),
      token: verificationCode(body.code),
      type: "email",
    });
    if (error)
      throw new AuthFailure(
        error.status === 429 ? 429 : 400,
        "That code is invalid or has expired. Check the code or request a new one.",
      );
    return json({ next: returnPath(body.next) });
  });
}

export function session(request: Request) {
  return handle(async () => {
    const body = await readForm(request, authConfig().site);
    const auth = await serverAuth();
    if (body.refresh === true) {
      const { error } = await auth.auth.refreshSession();
      if (error) {
        if (
          isAuthRetryableFetchError(error) ||
          error.status === 429 ||
          (error.status && error.status >= 500)
        )
          throw error;
        await clearAuthCookies();
        throw new AuthFailure(401, "Your session has ended. Sign in again to continue.");
      }
    }
    const { data: identity, error } = await auth.auth.getUser();
    if (error || !identity.user) {
      if (
        error &&
        (isAuthRetryableFetchError(error) ||
          error.status === 429 ||
          (error.status && error.status >= 500))
      )
        throw error;
      await clearAuthCookies();
      throw new AuthFailure(401, "Sign in to open your journal.");
    }
    const { data } = await auth.auth.getSession();
    if (!data.session) {
      await clearAuthCookies();
      throw new AuthFailure(401, "Your session has ended. Sign in again to continue.");
    }
    return json({
      accessToken: data.session.access_token,
      subject: identity.user.id,
      email: identity.user.email ?? null,
      expiresAt: data.session.expires_at,
      apiUrl: authConfig().api,
    });
  });
}

export function signOut(request: Request) {
  return handle(async () => {
    await readForm(request, authConfig().site);
    const auth = await serverAuth();
    const { error } = await auth.auth.signOut({ scope: "local" });
    // Keep cookies when the provider is unavailable so the user can retry revocation.
    if (error) throw new AuthFailure(503, "We couldn't finish signing out. Please try again.");
    await clearAuthCookies();
    return json({ next: "/browse" });
  });
}

export function oauth(request: Request) {
  return handle(async () => {
    const config = authConfig();
    const body = await readForm(request, config.site);
    const provider = config.providers.find((candidate) => candidate === body.provider);
    if (!provider)
      throw new AuthFailure(400, "This sign-in method isn't available yet. Use an email code.");
    const store = await cookies();
    store.set("wine-journal-return", returnPath(body.next), {
      httpOnly: true,
      secure: config.secure,
      sameSite: "lax",
      path: "/",
      maxAge: 600,
    });
    const auth = await serverAuth();
    const { data, error } = await auth.auth.signInWithOAuth({
      provider,
      options: { redirectTo: config.site + "/auth/callback", skipBrowserRedirect: true },
    });
    if (error || !data.url)
      throw new AuthFailure(503, "This sign-in method is unavailable. Try an email code.");
    return json({ url: data.url });
  });
}

export async function callback(request: Request) {
  const config = authConfig();
  const code = new URL(request.url).searchParams.get("code");
  const store = await cookies();
  const next = returnPath(store.get("wine-journal-return")?.value);
  store.delete("wine-journal-return");
  let success = false;
  try {
    if (code && code.length <= 2048) {
      const auth = await serverAuth();
      const { error } = await auth.auth.exchangeCodeForSession(code);
      success = !error;
    }
  } catch {
    /* A cancelled or unavailable provider returns to a recoverable sign-in page. */
  }
  const target = success ? next : `/auth/sign-in?error=callback&next=${encodeURIComponent(next)}`;
  return NextResponse.redirect(config.site + target, {
    status: 303,
    headers: { "Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer" },
  });
}
