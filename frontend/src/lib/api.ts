/** Typed API client for backend endpoints. */

import type {
  Assessment,
  ParcelDetail,
  ParcelSearchResult,
} from "../types/assessment";
import type { HomeMetadata } from "../types/home";

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

export async function getParcelFacts(
  ain: string,
): Promise<ParcelDetail | null> {
  const url = `${API_URL}/api/parcels/${encodeURIComponent(ain)}/facts`;
  const res = await fetch(url);

  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return (await res.json()) as ParcelDetail;
}

export async function getParcelAssessment(
  ain: string,
): Promise<Assessment | null> {
  const url = `${API_URL}/api/parcels/${encodeURIComponent(ain)}/assessment`;
  const res = await fetch(url);

  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return (await res.json()) as Assessment;
}

export async function getHomeMetadata(): Promise<HomeMetadata> {
  const res = await fetch(`${API_URL}/api/home`);

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return (await res.json()) as HomeMetadata;
}
