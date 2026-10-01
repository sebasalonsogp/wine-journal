"use client";

import { useEffect } from "react";
import { privateResetEvent } from "@/lib/session/private-drafts";

export function usePendingImages(active: boolean) {
  useEffect(() => {
    if (!active) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const follow = (event: MouseEvent) => {
      const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (
        !(link instanceof HTMLAnchorElement) ||
        link.target === "_blank" ||
        event.ctrlKey ||
        event.metaKey
      )
        return;
      if (
        link.hash &&
        link.origin === location.origin &&
        link.pathname === location.pathname &&
        link.search === location.search
      )
        return;
      if (event.defaultPrevented) return;
      event.preventDefault();
      event.stopPropagation();
      if (
        window.confirm(
          "Some images haven’t finished. Leave this page? Saved entries are kept, but selected files must be chosen again.",
        )
      ) {
        // One confirmation also clears guards for other selected images on this page.
        window.dispatchEvent(new Event("wine-journal-leave-images"));
        window.location.assign(link.href);
      }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", follow, true);
    const clear = () => {
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", follow, true);
    };
    window.addEventListener(privateResetEvent, clear);
    window.addEventListener("wine-journal-leave-images", clear);
    return () => {
      clear();
      window.removeEventListener(privateResetEvent, clear);
      window.removeEventListener("wine-journal-leave-images", clear);
    };
  }, [active]);
}
