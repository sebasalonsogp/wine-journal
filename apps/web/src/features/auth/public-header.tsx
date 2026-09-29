"use client";

import { useEffect, useRef, useState } from "react";
import { AppHeader } from "@/components/app-header";
import { authRequest, RequestFailure } from "@/lib/session/http";

export function PublicHeader() {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState("");
  const channel = useRef<BroadcastChannel | null>(null);
  const revision = useRef(0);

  useEffect(() => {
    let active = true;
    async function check() {
      const current = ++revision.current;
      try {
        await authRequest("/auth/session", {});
        if (active && current === revision.current) {
          setSignedIn(true);
          setError("");
        }
      } catch (failure) {
        if (!active || current !== revision.current) return;
        if (failure instanceof RequestFailure && failure.status === 401) {
          setSignedIn(false);
          setError("");
        } else {
          setSignedIn(null);
          setError("Couldn't check your session. Refocus this tab to try again.");
        }
      }
    }
    const authChannel = new BroadcastChannel("wine-journal-auth");
    channel.current = authChannel;
    authChannel.onmessage = () => void check();
    const visible = () => {
      if (document.visibilityState === "visible") void check();
    };
    const restore = (event: PageTransitionEvent) => {
      if (event.persisted) void check();
    };
    void check();
    window.addEventListener("focus", check);
    window.addEventListener("pageshow", restore);
    document.addEventListener("visibilitychange", visible);
    return () => {
      active = false;
      authChannel.close();
      channel.current = null;
      window.removeEventListener("focus", check);
      window.removeEventListener("pageshow", restore);
      document.removeEventListener("visibilitychange", visible);
    };
  }, []);

  async function signOut() {
    setEnding(true);
    setError("");
    ++revision.current;
    try {
      await authRequest("/auth/sign-out", {});
      ++revision.current;
      setSignedIn(false);
      channel.current?.postMessage("signed-out");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Please try signing out again.");
    } finally {
      setEnding(false);
    }
  }

  return (
    <>
      <AppHeader signedIn={signedIn} onSignOut={signOut} signingOut={ending} />
      {error && (
        <p role="alert" className="page-error">
          {error}
        </p>
      )}
    </>
  );
}
