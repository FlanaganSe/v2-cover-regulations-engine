/** Types matching the backend homepage metadata response. */

import type { ParcelSearchResult } from "./assessment";

export interface HomeSource {
  id: string;
  label: string;
  source_url: string | null;
  coverage_note: string;
}

export interface FeaturedParcel extends ParcelSearchResult {
  category: "clean_supported" | "multifamily" | "specific_plan" | "hpoz";
  label: string;
  description: string;
}

export interface HomeMetadata {
  data_as_of: string | null;
  supported_zone_classes: string[];
  sources: HomeSource[];
  featured_parcels: FeaturedParcel[];
}
