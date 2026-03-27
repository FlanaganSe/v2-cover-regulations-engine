/** Trust-first homepage content for the empty workspace state. */

import {
  BookOpen,
  Building2,
  Clock3,
  Database,
  Home,
  MapPinned,
  Scale,
  Sparkles,
} from "lucide-react";
import type { ParcelSearchResult } from "../types/assessment";
import type { FeaturedParcel, HomeMetadata } from "../types/home";
import type { RecentSearchItem } from "../lib/recentSearches";

interface HomePanelProps {
  metadata: HomeMetadata | null;
  metadataError: boolean;
  recentSearches: RecentSearchItem[];
  onSelectParcel: (result: ParcelSearchResult) => void;
}

const SUPPORTED_SCOPE = [
  "City of Los Angeles parcels only",
  "Residential-focused curated rule-pack coverage",
  "Deterministic zoning and standards first",
  "AI used only to explain grounded facts",
];

const LIMITATIONS = [
  "Chapter 1A / downtown zones are not supported yet",
  "Specific plans and HPOZ reduce confidence and require manual review",
  "Building footprints are available only for demo neighborhoods",
];

const FALLBACK_SOURCES = [
  {
    id: "parcels",
    label: "LA County Parcels",
    source_url: null,
    coverage_note:
      "Parcel geometry, addresses, and property facts filtered to LA City parcels.",
  },
  {
    id: "zoning",
    label: "NavigateLA Zoning",
    source_url: null,
    coverage_note:
      "Primary zoning layer used to determine base zone class and zone string.",
  },
  {
    id: "specific_plans",
    label: "Specific Plans",
    source_url: null,
    coverage_note:
      "Specific plan intersections are flagged because additional standards may apply.",
  },
  {
    id: "hpoz",
    label: "HPOZ",
    source_url: null,
    coverage_note:
      "Historic preservation overlay intersections are flagged for design review.",
  },
  {
    id: "community_plan_areas",
    label: "Community Plan Areas",
    source_url: null,
    coverage_note: "Used for community-plan context and Chapter 1A detection.",
  },
  {
    id: "general_plan_lu",
    label: "General Plan Land Use",
    source_url: null,
    coverage_note: "Used as policy context alongside the zoning assessment.",
  },
  {
    id: "city_boundaries",
    label: "City Boundaries",
    source_url: null,
    coverage_note:
      "Used to confirm whether a parcel is inside the City of Los Angeles.",
  },
  {
    id: "buildings",
    label: "LARIAC Buildings",
    source_url: null,
    coverage_note:
      "Building footprints are seeded only for demo neighborhoods: Silver Lake, Venice, and Eagle Rock.",
  },
];

const CONFIDENCE_LEVELS = [
  {
    label: "High",
    description:
      "Supported residential parcel with no major modifiers or overlays.",
    className: "border-green-200 bg-green-50 text-green-800",
  },
  {
    label: "Medium",
    description:
      "Supported parcel with qualifiers, overlays, or extra review needs.",
    className: "border-amber-200 bg-amber-50 text-amber-800",
  },
  {
    label: "Low",
    description:
      "Unsupported, ambiguous, or overlay-heavy cases that need manual review.",
    className: "border-red-200 bg-red-50 text-red-800",
  },
];

function ParcelButton({
  title,
  subtitle,
  onClick,
}: {
  title: string;
  subtitle: string;
  onClick: () => void;
}): React.JSX.Element {
  return (
    <button
      onClick={onClick}
      className="w-full rounded-xl border border-gray-200 bg-white p-3 text-left shadow-sm transition hover:border-blue-300 hover:bg-blue-50"
    >
      <div className="text-sm font-semibold text-gray-900">{title}</div>
      <div className="mt-1 text-xs leading-relaxed text-gray-600">
        {subtitle}
      </div>
    </button>
  );
}

function FeaturedParcels({
  featuredParcels,
  onSelectParcel,
}: {
  featuredParcels: FeaturedParcel[];
  onSelectParcel: (result: ParcelSearchResult) => void;
}): React.JSX.Element | null {
  if (featuredParcels.length === 0) return null;

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Sparkles className="h-4 w-4 text-blue-600" />
        Featured parcels
      </div>
      <div className="space-y-2">
        {featuredParcels.map((parcel) => (
          <ParcelButton
            key={`${parcel.category}:${parcel.ain}`}
            title={parcel.label}
            subtitle={[
              parcel.description,
              parcel.address ?? "Address unavailable",
              parcel.zone_class ? `Zone ${parcel.zone_class}` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
            onClick={() => onSelectParcel(parcel)}
          />
        ))}
      </div>
    </section>
  );
}

function RecentSearches({
  recentSearches,
  onSelectParcel,
}: {
  recentSearches: RecentSearchItem[];
  onSelectParcel: (result: ParcelSearchResult) => void;
}): React.JSX.Element | null {
  if (recentSearches.length === 0) return null;

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Clock3 className="h-4 w-4 text-blue-600" />
        Recent searches
      </div>
      <div className="space-y-2">
        {recentSearches.map((parcel) => (
          <ParcelButton
            key={`recent:${parcel.ain}`}
            title={parcel.address ?? parcel.apn ?? parcel.ain}
            subtitle={[
              `APN ${parcel.apn ?? parcel.ain}`,
              parcel.zone_class ? `Zone ${parcel.zone_class}` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
            onClick={() => onSelectParcel(parcel)}
          />
        ))}
      </div>
    </section>
  );
}

function SourcesSection({
  metadata,
  metadataError,
}: {
  metadata: HomeMetadata | null;
  metadataError: boolean;
}): React.JSX.Element {
  const formattedDate =
    metadata?.data_as_of != null
      ? new Date(metadata.data_as_of).toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        })
      : null;

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Database className="h-4 w-4 text-blue-600" />
        Data sources
      </div>
      {formattedDate ? (
        <p className="text-xs text-gray-500">
          Latest data snapshot: {formattedDate}
        </p>
      ) : (
        <p className="text-xs text-gray-500">
          Latest data freshness is unavailable in this environment.
        </p>
      )}
      {metadataError && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
          Live source metadata could not be loaded. Static scope guidance is
          still shown.
        </p>
      )}
      <div className="space-y-2">
        {(metadata?.sources ?? FALLBACK_SOURCES).map((source) => (
          <div
            key={source.id}
            className="rounded-lg border border-gray-200 bg-white p-3"
          >
            <div className="text-sm font-medium text-gray-900">
              {source.label}
            </div>
            <div className="mt-1 text-xs leading-relaxed text-gray-600">
              {source.coverage_note}
            </div>
            {source.source_url && (
              <a
                href={source.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex text-xs font-medium text-blue-600 hover:underline"
              >
                View source
              </a>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export function HomePanel({
  metadata,
  metadataError,
  recentSearches,
  onSelectParcel,
}: HomePanelProps): React.JSX.Element {
  const supportedZoneCount = metadata?.supported_zone_classes.length;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-blue-700">
          <Home className="h-4 w-4" />
          Regulation workspace
        </div>
        <h2 className="mt-2 text-xl font-semibold text-gray-900">
          Understand what can be confidently built on a parcel.
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-gray-600">
          Search by address or APN to review parcel facts, zoning, overlays,
          development standards, ADU guidance, and a grounded explanation of the
          result.
        </p>
        <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 p-3 text-xs leading-relaxed text-blue-900">
          {supportedZoneCount != null
            ? `The current rule pack covers ${supportedZoneCount} curated residential zone classes.`
            : "The current rule pack covers a curated residential subset of LA City zoning."}
        </div>
      </section>

      <FeaturedParcels
        featuredParcels={metadata?.featured_parcels ?? []}
        onSelectParcel={onSelectParcel}
      />

      <RecentSearches
        recentSearches={recentSearches}
        onSelectParcel={onSelectParcel}
      />

      {recentSearches.length === 0 &&
        (metadata?.featured_parcels.length ?? 0) === 0 && (
          <section className="rounded-2xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-600">
            Start with an address or APN in Los Angeles. The search bar supports
            parcel addresses and formatted APNs like{" "}
            <span className="font-medium">1234-567-890</span>.
          </section>
        )}

      <section className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <MapPinned className="h-4 w-4 text-blue-600" />
          Supported scope
        </div>
        <div className="space-y-2">
          {SUPPORTED_SCOPE.map((item) => (
            <div
              key={item}
              className="rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700"
            >
              {item}
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <Building2 className="h-4 w-4 text-blue-600" />
          Important limitations
        </div>
        <div className="space-y-2">
          {LIMITATIONS.map((item) => (
            <div
              key={item}
              className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
            >
              {item}
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <Scale className="h-4 w-4 text-blue-600" />
          Confidence guide
        </div>
        <div className="space-y-2">
          {CONFIDENCE_LEVELS.map((level) => (
            <div
              key={level.label}
              className={`rounded-lg border p-3 text-sm ${level.className}`}
            >
              <div className="font-semibold">{level.label}</div>
              <div className="mt-1 leading-relaxed">{level.description}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <BookOpen className="h-4 w-4 text-blue-600" />
          How this works
        </div>
        <div className="space-y-2">
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700">
            Parcel match and zoning context are resolved from GIS layers in
            PostGIS.
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700">
            Development standards and confidence come from deterministic rules,
            not the AI.
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700">
            The AI summary restates grounded facts and citations to make the
            result easier to read.
          </div>
        </div>
      </section>

      <SourcesSection metadata={metadata} metadataError={metadataError} />
    </div>
  );
}
