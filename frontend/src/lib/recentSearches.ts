/** LocalStorage helpers for recent successful parcel views. */

import type { ParcelSearchResult } from "../types/assessment";

export interface RecentSearchItem extends ParcelSearchResult {
  lastViewedAt: string;
}

const STORAGE_KEY = "recentParcelSearches";
const MAX_RECENT_SEARCHES = 5;

function isRecentSearchItem(value: unknown): value is RecentSearchItem {
  if (typeof value !== "object" || value === null) return false;

  const item = value as Record<string, unknown>;
  return (
    typeof item.ain === "string" &&
    typeof item.lastViewedAt === "string" &&
    (typeof item.apn === "string" || item.apn === null) &&
    (typeof item.address === "string" || item.address === null) &&
    (typeof item.zone_class === "string" || item.zone_class === null)
  );
}

export function loadRecentSearches(): RecentSearchItem[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isRecentSearchItem).slice(0, MAX_RECENT_SEARCHES);
  } catch {
    return [];
  }
}

export function addRecentSearch(
  recentSearches: RecentSearchItem[],
  search: ParcelSearchResult,
): RecentSearchItem[] {
  const nextItem: RecentSearchItem = {
    ...search,
    lastViewedAt: new Date().toISOString(),
  };

  return [
    nextItem,
    ...recentSearches.filter((item) => item.ain !== search.ain),
  ].slice(0, MAX_RECENT_SEARCHES);
}

export function persistRecentSearches(
  recentSearches: RecentSearchItem[],
): void {
  if (typeof window === "undefined") return;

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(recentSearches));
}
