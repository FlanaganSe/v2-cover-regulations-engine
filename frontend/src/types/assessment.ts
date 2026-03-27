/** TypeScript types matching backend Pydantic models exactly. */

export interface ParcelSearchResult {
  ain: string;
  apn: string | null;
  address: string | null;
  zone_class: string | null;
}

export interface ParcelFacts {
  ain: string;
  apn: string | null;
  address: string | null;
  center_lat: number | null;
  center_lon: number | null;
  lot_sqft: number | null;
  year_built: number | null;
  use_description: string | null;
  bedrooms: number | null;
  sqft_main: number | null;
}

export interface Scope {
  in_la_city: boolean;
  supported_zone: boolean;
  chapter_1a: boolean;
}

export interface Zoning {
  zone_string: string | null;
  zone_class: string | null;
  height_district: string | null;
  q_flag: boolean;
  d_flag: boolean;
  t_flag: boolean;
  suffixes: string[];
}

export interface OverlayRef {
  name: string;
  url: string | null;
}

export interface Overlays {
  specific_plan: OverlayRef | null;
  hpoz: OverlayRef | null;
  community_plan: string | null;
  general_plan_lu: string | null;
}

export interface Standards {
  height_ft: number | null;
  stories: number | null;
  far_or_rfa: number | null;
  far_type: string | null;
  front_setback_ft: string | null;
  side_setback_ft: string | null;
  rear_setback_ft: string | null;
  density_description: string | null;
  allowed_uses: string[];
}

export interface Adu {
  allowed: boolean;
  max_sqft: number;
  setbacks_ft: number;
  notes: string;
}

export interface ConfidenceResponse {
  level: string;
  reasons: string[];
}

export interface Assessment {
  summary: string;
  citations: string[];
  caveats: string[];
  llm_available: boolean;
}

export interface Metadata {
  data_as_of: string | null;
  source_urls: string[];
}

export interface ParcelDetail {
  parcel: ParcelFacts;
  scope: Scope;
  zoning: Zoning;
  overlays: Overlays;
  standards: Standards;
  adu: Adu;
  confidence: ConfidenceResponse;
  assessment: Assessment;
  metadata: Metadata;
}
