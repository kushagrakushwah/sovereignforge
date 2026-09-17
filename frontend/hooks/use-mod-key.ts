"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};
const isApple = () => /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

/** "⌘" on Apple platforms, "Ctrl" elsewhere. Renders "Ctrl" on the server. */
export function useModKey() {
  return useSyncExternalStore(
    subscribe,
    () => (isApple() ? "⌘" : "Ctrl"),
    () => "Ctrl",
  );
}
