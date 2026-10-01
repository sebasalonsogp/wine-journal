"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { createTransport } from "@/lib/api/transport";
import { RequestFailure } from "@/lib/session/http";
import { clearPrivateDrafts } from "@/lib/session/private-drafts";
import { CaptureFields } from "./capture-fields";
import { CaptureOccasion } from "./capture-occasion";
import { PhotoWorkspace } from "@/features/media/photo-workspace";
import {
  entryBody,
  newDraft,
  readDraft,
  writeDraft,
  removeDraft,
  type Draft,
  type Fields,
} from "./draft";

export function CaptureForm({ wineId }: { wineId?: string }) {
  const [api] = useState(createTransport);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState<"checking" | "ready" | "locked" | "error">("checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [savedEntry, setSavedEntry] = useState<{ id: string; userWineId: string } | null>(null);
  const photoCount = useRef(0);
  const selectedPhotos = useCallback((count: number) => {
    photoCount.current = count;
  }, []);
  const submitting = useRef(false);
  const checkVersion = useRef(0);

  const checkAccount = useCallback(async () => {
    if (submitting.current) return;
    const version = ++checkVersion.current;
    try {
      let owner: string | null = null;
      try {
        owner = (await api.account()).id;
      } catch (failure) {
        if (!(failure instanceof RequestFailure) || failure.status !== 401) throw failure;
      }
      if (version !== checkVersion.current) return;
      let saved = readDraft();
      if (saved?.ownerId && !owner) {
        setDraft(null);
        setStatus("locked");
        return;
      }
      if (saved?.ownerId && saved.ownerId !== owner) {
        removeDraft();
        saved = null;
        setNotice("The previous account’s unfinished entry was cleared.");
      }
      if (!saved && wineId) {
        if (!owner) {
          setStatus("locked");
          return;
        }
        const wine = await api.call((client, signal) =>
          client.GET("/api/v1/me/wines/{wine_id}", {
            params: { path: { wine_id: wineId } },
            signal,
          }),
        );
        if (version !== checkVersion.current) return;
        saved = newDraft(owner);
        saved.fields = {
          ...saved.fields,
          name: wine.name,
          producer: wine.producer ?? "",
          releaseId: wine.releaseId,
          vintageStatus: wine.vintageStatus as Fields["vintageStatus"],
          year: wine.year?.toString() ?? "",
          edition: wine.edition ?? "",
        };
      }
      const next = saved ? { ...saved, ownerId: owner } : newDraft(owner);
      setDraft(next);
      if (saved) writeDraft(next);
      setStatus("ready");
    } catch (failure) {
      if (version !== checkVersion.current) return;
      setError(failure instanceof Error ? failure.message : "Please try again.");
      setStatus("error");
    }
  }, [api, wineId]);

  useEffect(() => {
    const checks = checkVersion;
    // Restore browser-only draft state after mounting, alongside the session check.
    void Promise.resolve().then(checkAccount);
    const channel = new BroadcastChannel("wine-journal-auth");
    channel.onmessage = (event) => {
      ++checkVersion.current;
      api.clear();
      if (event.data === "signed-out") {
        clearPrivateDrafts();
        setDraft(null);
        setSavedEntry(null);
        setStatus("locked");
        window.location.replace("/browse");
      } else {
        submitting.current = false;
        setSavedEntry(null);
        setStatus("checking");
        void checkAccount();
      }
    };
    const restore = (event: PageTransitionEvent) => {
      if (event.persisted) window.location.reload();
    };
    window.addEventListener("pageshow", restore);
    return () => {
      ++checks.current;
      channel.close();
      window.removeEventListener("pageshow", restore);
    };
  }, [api, checkAccount]);

  function change(values: Partial<Fields>) {
    if (!draft || draft.intentKey) return;
    const next = { ...draft, fields: { ...draft.fields, ...values } };
    setDraft(next);
    if (!writeDraft(next))
      setNotice("Draft storage is unavailable. Keep this tab open until you finish saving.");
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || savedEntry || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    let active = draft;
    const version = checkVersion.current;
    try {
      const account = await api.account();
      if (draft.ownerId && draft.ownerId !== account.id) {
        removeDraft();
        setDraft(newDraft(account.id));
        setError(
          "Your account changed. The previous draft was cleared; enter a wine for this account.",
        );
        return;
      }
      active = { ...draft, ownerId: account.id, intentKey: draft.intentKey ?? crypto.randomUUID() };
      setDraft(active);
      if (!writeDraft(active)) {
        active = { ...active, intentKey: null };
        setDraft(active);
        setError(
          "Your browser couldn’t keep the save key. Enable session storage, then try again.",
        );
        return;
      }
      const body = entryBody(active.fields);
      const entry = await api.call((client, signal) =>
        client.POST("/api/v1/entries", {
          body,
          params: { header: { "idempotency-key": active.intentKey! } },
          signal,
        }),
      );
      removeDraft();
      if (version !== checkVersion.current) return;
      if (photoCount.current > 0) {
        setSavedEntry({ id: entry.id, userWineId: entry.userWineId });
        return;
      }
      // A document navigation drops old query caches before reading the persisted entry.
      window.location.replace(`/my-wines/${entry.userWineId}`);
    } catch (failure) {
      if (version !== checkVersion.current) return;
      if (failure instanceof RequestFailure && failure.status === 401) {
        if (writeDraft(active)) window.location.replace("/auth/sign-in?next=%2Fcapture");
        else
          setError(
            "Draft storage is blocked. Enable session storage in your browser before signing in.",
          );
      } else {
        if (failure instanceof RequestFailure && [404, 422].includes(failure.status)) {
          active = { ...active, intentKey: null };
          setDraft(active);
          writeDraft(active);
        }
        setError(failure instanceof Error ? failure.message : "Please try saving again.");
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <main id="main" className="page-content capture-page">
      <Link className="back-link" href="/my-wines" prefetch={false}>
        Back to My wines
      </Link>
      <div className="journal-heading">
        <h1>I tried this wine.</h1>
        <p className="page-intro">The wine and date are all you need.</p>
      </div>
      {status === "checking" ? (
        <p role="status">Opening your entry…</p>
      ) : status === "locked" ? (
        <section className="empty-state">
          <h2>Your unfinished entry is private.</h2>
          <p>Sign in to the same account to continue.</p>
          <Link className="button" href="/auth/sign-in?next=%2Fcapture">
            Sign in to continue
          </Link>
        </section>
      ) : status === "error" ? (
        <section>
          <p role="alert">{error}</p>
          <button className="button" onClick={() => void checkAccount()}>
            Try again
          </button>
        </section>
      ) : (
        draft && (
          <>
            {savedEntry ? (
              <section className="save-notice" aria-labelledby="entry-saved-title">
                <h2 id="entry-saved-title">Your entry is saved.</h2>
                <p>The wine, date and notes are safe. Photos upload separately below.</p>
                <a className="button" href={`/my-wines/${savedEntry.userWineId}`}>
                  View wine
                </a>
              </section>
            ) : (
              <form className="capture-form" onSubmit={submit} aria-busy={busy}>
                {notice && (
                  <p className="form-message" role="status">
                    {notice}
                  </p>
                )}
                {draft.intentKey && !busy && (
                  <p className="save-notice" role="status">
                    This entry has an unconfirmed save. Retry to check and finish the same entry.
                    Your details are kept unchanged to prevent a duplicate.
                  </p>
                )}
                <fieldset disabled={busy || Boolean(draft.intentKey)}>
                  <legend className="sr-only">Wine and drinking date</legend>
                  <CaptureFields fields={draft.fields} change={change} />
                  <div className="form-field">
                    <label htmlFor="capture-notes">
                      Quick notes <span>optional</span>
                    </label>
                    <textarea
                      id="capture-notes"
                      rows={3}
                      maxLength={10000}
                      value={draft.fields.notes}
                      onChange={(event) => change({ notes: event.target.value })}
                      placeholder="A first impression, or something to remember later"
                    />
                  </div>
                  <CaptureOccasion
                    key={draft.ownerId ?? "guest"}
                    fields={draft.fields}
                    change={change}
                    owner={draft.ownerId}
                    api={api}
                  />
                </fieldset>
                {error && (
                  <p className="form-message" role="alert">
                    {error}
                  </p>
                )}
                <div className="capture-actions">
                  <button type="submit" className="button" disabled={busy}>
                    {busy
                      ? "Saving…"
                      : draft.intentKey
                        ? "Retry save"
                        : draft.ownerId
                          ? "Save entry"
                          : "Sign in to save"}
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(
                          draft.intentKey
                            ? "This entry may already be saved. Discard this draft and check My wines before creating another?"
                            : "Discard this unfinished entry?",
                        )
                      ) {
                        removeDraft();
                        window.location.replace("/my-wines");
                      }
                    }}
                  >
                    Discard draft
                  </button>
                </div>
                {!draft.ownerId && (
                  <p className="form-footnote">Your input will be kept while you sign in.</p>
                )}
                <p className="form-footnote">
                  Saved entries stay private. You can add more notes, time and location later.
                </p>
              </form>
            )}
            {draft.ownerId ? (
              <PhotoWorkspace
                key={draft.ownerId}
                api={api}
                entryId={savedEntry?.id}
                onSelectionChange={selectedPhotos}
              />
            ) : (
              <p className="form-footnote">You can add private photos after signing in.</p>
            )}
          </>
        )
      )}
    </main>
  );
}
