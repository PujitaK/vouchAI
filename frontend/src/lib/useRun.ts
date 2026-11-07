"use client";

import { useEffect, useState } from "react";

import { ADMIN_KEY_STORAGE_KEY } from "@/lib/useAdminKey";
import type { Run, SimStatus } from "@/lib/types";

const STATIC_RUN_PATH = "/cached_run.json";
const DEFAULT_API_URL = "http://127.0.0.1:8000";
const POLL_INTERVAL_MS = 1400;
const LIVE_QUERY_PARAM = "live";

export interface UseRunOptions {
  live?: boolean;
}

export interface UseRunResult {
  run: Run | null;
  loading: boolean;
  error: string | null;
}

function wait(ms: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "The simulation could not be loaded.";
}

function readAdminKey(): string {
  if (typeof window === "undefined") return "";
  try {
    return (window.sessionStorage.getItem(ADMIN_KEY_STORAGE_KEY) ?? "").trim();
  } catch {
    return "";
  }
}

function getLiveAdminKey(): string | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  if (params.get(LIVE_QUERY_PARAM) !== "1") return null;
  const adminKey = readAdminKey();
  return adminKey.length > 0 ? adminKey : null;
}

async function fetchJson<T>(url: string, init: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${url}`);
  }
  return (await response.json()) as T;
}

async function loadStaticRun(signal: AbortSignal): Promise<Run> {
  return fetchJson<Run>(STATIC_RUN_PATH, { signal });
}

async function loadLiveRun(signal: AbortSignal, adminKey: string): Promise<Run> {
  const apiUrl = (
    process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL
  ).replace(/\/+$/, "");
  const headers = { "X-API-Key": adminKey };

  const started = await fetch(`${apiUrl}/sim/run`, {
    method: "POST",
    signal,
    cache: "no-store",
    headers,
  });

  if (!started.ok && started.status !== 409) {
    throw new Error(`Could not start simulation (${started.status})`);
  }

  for (;;) {
    const status = await fetchJson<SimStatus>(`${apiUrl}/sim/status`, {
      signal,
      headers,
    });

    if (status.state === "error") {
      throw new Error(status.error ?? "The simulation failed.");
    }

    if (status.state === "done") {
      break;
    }

    await wait(POLL_INTERVAL_MS);
  }

  return fetchJson<Run>(`${apiUrl}/sim/cached`, { signal, headers });
}

export function useRun({ live }: UseRunOptions = {}): UseRunResult {
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      let staticRun: Run | null = null;
      let staticError: string | null = null;

      try {
        staticRun = await loadStaticRun(controller.signal);
      } catch (caught) {
        if (!isAbortError(caught)) {
          staticError = errorMessage(caught);
        }
      }

      if (cancelled) return;

      if (staticRun) {
        setRun(staticRun);
        setError(null);
      } else if (staticError) {
        setError(staticError);
      }
      setLoading(false);

      if (live === false) return;

      const adminKey = getLiveAdminKey();
      if (!adminKey) return;

      try {
        const liveRun = await loadLiveRun(controller.signal, adminKey);
        if (!cancelled) {
          setRun(liveRun);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled && !isAbortError(caught) && !staticRun) {
          setError(staticError ?? errorMessage(caught));
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [live]);

  return { run, loading, error };
}
