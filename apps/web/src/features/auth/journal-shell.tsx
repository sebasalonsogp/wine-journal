"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { AppHeader } from "@/components/app-header";
import { createTransport, type Account } from "@/lib/api/transport";
import { authRequest, RequestFailure } from "@/lib/session/http";
import { returnPath } from "./validation";

const AccountContext = createContext<Account | null>(null);
export function useAccount() {
  return useContext(AccountContext);
}

export function JournalShell({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: 0 } } }),
  );
  return (
    <QueryClientProvider client={queryClient}>
      <VerifiedJournal>{children}</VerifiedJournal>
    </QueryClientProvider>
  );
}

function VerifiedJournal({ children }: { children: React.ReactNode }) {
  const [transport] = useState(createTransport);
  const queries = useQueryClient();
  const path = usePathname();
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState("");
  const authChannel = useRef<BroadcastChannel | null>(null);
  const account = useQuery({
    queryKey: ["account"],
    queryFn: () => transport.account(),
    refetchOnWindowFocus: "always",
    enabled: !ending,
  });

  useEffect(() => {
    if (!ending && account.error instanceof RequestFailure && account.error.status === 401) {
      transport.clear();
      queries.clear();
      window.location.replace(
        `/auth/sign-in?next=${encodeURIComponent(returnPath(path))}&error=session`,
      );
    }
  }, [account.error, ending, path, queries, transport]);

  useEffect(() => {
    const channel = new BroadcastChannel("wine-journal-auth");
    authChannel.current = channel;
    channel.onmessage = () => {
      transport.clear();
      queries.clear();
      window.location.replace("/auth/sign-in?error=session");
    };
    const restore = (event: PageTransitionEvent) => {
      if (event.persisted) window.location.reload();
    };
    window.addEventListener("pageshow", restore);
    return () => {
      authChannel.current = null;
      channel.close();
      window.removeEventListener("pageshow", restore);
    };
  }, [queries, transport]);

  async function signOut() {
    setEnding(true);
    setError("");
    try {
      await authRequest("/auth/sign-out", {});
      transport.clear();
      queries.clear();
      authChannel.current?.postMessage("signed-out");
      window.location.replace("/browse");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Please try signing out again.");
      setEnding(false);
    }
  }

  return (
    <>
      <AppHeader signedIn onSignOut={signOut} signingOut={ending} />
      {error && (
        <p role="alert" className="page-error">
          {error}
        </p>
      )}
      {ending || account.isPending || account.isFetching ? (
        <main id="main" className="page-content" aria-busy="true">
          <p role="status">{ending ? "Signing out…" : "Opening your journal…"}</p>
        </main>
      ) : account.error ? (
        <main id="main" className="page-content">
          <h1>We couldn’t open your journal</h1>
          <p role="alert">
            {account.error instanceof RequestFailure
              ? account.error.message
              : "Check your connection and try again."}
          </p>
          <button className="button" onClick={() => void account.refetch()}>
            Try again
          </button>
        </main>
      ) : (
        <AccountContext value={account.data}>{children}</AccountContext>
      )}
    </>
  );
}
