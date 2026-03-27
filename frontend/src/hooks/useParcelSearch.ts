/** Debounced parcel search hook with abort support. */

import { useCallback, useEffect, useRef, useState } from "react";
import { searchParcels } from "../lib/api";
import type { ParcelSearchResult } from "../types/assessment";

const DEBOUNCE_MS = 300;

export function useParcelSearch(): {
  query: string;
  setQuery: (q: string) => void;
  results: ParcelSearchResult[];
  isLoading: boolean;
} {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ParcelSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const doSearch = useCallback((q: string) => {
    abortRef.current?.abort();

    const trimmed = q.trim();
    if (!trimmed) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);

    searchParcels(trimmed, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setResults(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (!controller.signal.aborted) {
          setResults([]);
          setIsLoading(false);
        }
      });
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => doSearch(query), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query, doSearch]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return { query, setQuery, results, isLoading };
}
