/** Typed API client for backend endpoints. */

import type { ParcelDetail, ParcelSearchResult } from "../types/assessment";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function searchParcels(
  query: string,
  signal?: AbortSignal,
): Promise<ParcelSearchResult[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];

  const url = `${API_URL}/api/parcels/search?q=${encodeURIComponent(trimmed)}`;
  const res = await fetch(url, { signal });

  if (!res.ok) return [];
  return (await res.json()) as ParcelSearchResult[];
}

export async function getParcelDetail(
  ain: string,
): Promise<ParcelDetail | null> {
  const url = `${API_URL}/api/parcels/${encodeURIComponent(ain)}`;
  const res = await fetch(url);

  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return (await res.json()) as ParcelDetail;
}
