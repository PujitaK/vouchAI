"use client";

import { useCallback, useSyncExternalStore } from "react";

export const ADMIN_KEY_STORAGE_KEY = "vouchai.adminKey";
const listeners = new Set<() => void>();
let memoryValue = "";

function readStoredKey(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(ADMIN_KEY_STORAGE_KEY) ?? "";
  } catch {
    return memoryValue;
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): string {
  return readStoredKey();
}

function getServerSnapshot(): string {
  return "";
}

function emitChange(): void {
  for (const listener of listeners) {
    listener();
  }
}

export function useAdminKey() {
  const adminKey = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );

  const setAdminKey = useCallback((value: string) => {
    memoryValue = value;
    if (typeof window !== "undefined") {
      try {
        if (value) {
          window.sessionStorage.setItem(ADMIN_KEY_STORAGE_KEY, value);
        } else {
          window.sessionStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
        }
      } catch {
        memoryValue = value;
      }
    }
    emitChange();
  }, []);

  return { adminKey, setAdminKey };
}
