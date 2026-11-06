"use client";

import { useEffect, useState } from "react";

import type { Run, SimStatus } from "@/lib/types";

const STATIC_RUN_PATH = "/cached_run.json";
const DEFAULT_API_URL = "http://127.0.0.1:8000";
const POLL_INTERVAL_MS = 1400;

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

async function loadLiveRun(signal: AbortSignal): Promise<Run> {
  const apiUrl = (
    process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL
  ).replace(/\/+$/, "");

  const started = await fetch(`${apiUrl}/sim/run`, {
    method: "POST",
    signal,
    cache: "no-store",
  });

  if (!started.ok && started.status !== 409) {
    throw new Error(`Could not start simulation (${started.status})`);
  }

  for (;;) {
    const status = await fetchJson<SimStatus>(`${apiUrl}/sim/status`, {
      signal,
    });

    if (status.state === "error") {
      throw new Error(status.error ?? "The simulation failed.");
    }

    if (status.state === "done") {
      break;
    }

    await wait(POLL_INTERVAL_MS);
  }

  return fetchJson<Run>(`${apiUrl}/sim/cached`, { signal });
}

export function useRun({ live }: UseRunOptions = {}): UseRunResult {
  const liveMode = live ?? Boolean(process.env.NEXT_PUBLIC_API_URL);
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      try {
        const next = liveMode
          ? await loadLiveRun(controller.signal)
          : await loadStaticRun(controller.signal);
        if (!cancelled) {
          setRun(next);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled && !isAbortError(caught)) {
          setError(errorMessage(caught));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [liveMode]);

  return { run, loading, error };
}
