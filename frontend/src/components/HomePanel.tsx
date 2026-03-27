/** Home sidebar: hero, recent searches, featured parcels, how-it-works, data sources. */

import { CheckCircle2, ChevronRight, Clock3 } from "lucide-react";
import type { RecentSearchItem } from "../lib/recentSearches";
import type { ParcelSearchResult } from "../types/assessment";
import type { FeaturedParcel, HomeMetadata, HomeSource } from "../types/home";

interface HomePanelProps {
  metadata: HomeMetadata | null;
  metadataError: boolean;
  recentSearches: RecentSearchItem[];
  onSelectParcel: (result: ParcelSearchResult) => void;
}

const HOW_IT_WORKS = [
  {
    step: 1,
    title: "Search a parcel",
    description:
      "Enter an address or APN to look up any residential parcel in Los Angeles.",
  },
  {
    step: 2,
    title: "Review zoning details",
    description:
      "View development standards, overlays, setbacks, density limits, and allowed uses.",
  },
  {
    step: 3,
    title: "Read the assessment",
    description:
      "Get an automated summary with confidence level, citations, and caveats.",
  },
];

const FALLBACK_SOURCES: HomeSource[] = [
  {
    id: "parcels",
    label: "LA County Assessor",
    source_url: null,
    coverage_note: "Parcel geometry, lot size, year built",
  },
  {
    id: "zoning",
    label: "ZIMAS",
    source_url: null,
    coverage_note: "Zone string, height district, overlays",
  },
  {
    id: "lamc",
    label: "LAMC Chapter 1",
    source_url: null,
    coverage_note: "Development standards, setbacks, density",
  },
];

function Divider(): React.JSX.Element {
  return <hr className="border-border-subtle" />;
}

function SectionLabel({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <h3 className="text-[11px] font-semibold tracking-widest text-text-muted uppercase">
      {children}
    </h3>
  );
}

function ParcelCard({
  title,
  address,
  zoneBadge,
  onClick,
}: {
  title: string;
  address: string;
  zoneBadge: string | null;
  onClick: () => void;
}): React.JSX.Element {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-lg border border-border-default bg-bg-card p-3 text-left shadow-card transition-colors hover:border-accent-primary/30 hover:bg-bg-hover"
    >
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold text-text-primary">{title}</div>
        <div className="mt-0.5 text-xs text-text-muted">{address}</div>
        {zoneBadge && (
          <span className="mt-1 inline-block rounded bg-accent-primary-light px-1.5 py-0.5 text-[10px] font-semibold text-accent-primary">
            {zoneBadge}
          </span>
        )}
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-text-tertiary" />
    </button>
  );
}

function FeaturedParcels({
  parcels,
  onSelect,
}: {
  parcels: FeaturedParcel[];
  onSelect: (result: ParcelSearchResult) => void;
}): React.JSX.Element | null {
  if (parcels.length === 0) return null;

  return (
    <section className="space-y-3">
      <SectionLabel>Featured parcels</SectionLabel>
      <div className="space-y-2">
        {parcels.map((parcel) => (
          <ParcelCard
            key={`${parcel.category}:${parcel.ain}`}
            title={parcel.label}
            address={parcel.address ?? "Address unavailable"}
            zoneBadge={parcel.zone_class}
            onClick={() => onSelect(parcel)}
          />
        ))}
      </div>
    </section>
  );
}

function RecentSearches({
  searches,
  onSelect,
}: {
  searches: RecentSearchItem[];
  onSelect: (result: ParcelSearchResult) => void;
}): React.JSX.Element | null {
  if (searches.length === 0) return null;

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-1.5">
        <Clock3 className="h-3.5 w-3.5 text-text-muted" />
        <SectionLabel>Recent searches</SectionLabel>
      </div>
      <div className="space-y-2">
        {searches.map((search) => (
          <ParcelCard
            key={`recent:${search.ain}`}
            title={search.address ?? search.apn ?? search.ain}
            address={`APN ${search.apn ?? search.ain}`}
            zoneBadge={search.zone_class}
            onClick={() => onSelect(search)}
          />
        ))}
      </div>
    </section>
  );
}

function DataSourcesList({
  metadata,
  metadataError,
}: {
  metadata: HomeMetadata | null;
  metadataError: boolean;
}): React.JSX.Element {
  const sources = metadata?.sources ?? FALLBACK_SOURCES;

  const formattedDate =
    metadata?.data_as_of != null
      ? new Date(metadata.data_as_of).toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        })
      : null;

  return (
    <section className="space-y-3">
      <SectionLabel>Data sources</SectionLabel>
      {formattedDate && (
        <p className="text-xs text-text-muted">
          Latest data snapshot: {formattedDate}
        </p>
      )}
      {metadataError && (
        <p className="rounded-md border border-confidence-medium/30 bg-confidence-medium-bg p-2 text-xs text-confidence-medium">
          Live source metadata could not be loaded. Static scope guidance is
          still shown.
        </p>
      )}
      <ul className="space-y-2">
        {sources.map((source) => (
          <li
            key={source.id}
            className="flex items-baseline gap-2 text-xs text-text-secondary"
          >
            <span className="text-text-tertiary">&bull;</span>
            <span>
              <span className="font-medium">{source.label}</span>
              <span className="text-text-muted">
                {"  —  "}
                {source.coverage_note}
              </span>
            </span>
          </li>
        ))}
      </ul>
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
    <div className="space-y-7">
      {/* Hero */}
      <section>
        <p className="text-[11px] font-semibold tracking-widest text-accent-primary uppercase">
          Regulation workspace
        </p>
        <h2 className="mt-3 text-[22px] font-bold leading-snug text-text-primary">
          Understand what can be confidently built on a parcel.
        </h2>
        <p className="mt-3 text-[13px] leading-relaxed text-text-secondary">
          Search by address or APN to review parcel facts, zoning, overlays,
          development standards, ADU guidance, and a grounded explanation of the
          result.
        </p>
        <div className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-accent-teal/20 bg-accent-teal-light px-3 py-2 text-xs font-medium text-accent-teal">
          <CheckCircle2 className="h-3.5 w-3.5" />
          {supportedZoneCount != null
            ? `${supportedZoneCount} curated residential zone classes covered`
            : "Curated residential zone classes covered"}
        </div>
      </section>

      <Divider />

      {/* Recent Searches (conditional) */}
      {recentSearches.length > 0 && (
        <>
          <RecentSearches searches={recentSearches} onSelect={onSelectParcel} />
          <Divider />
        </>
      )}

      {/* Featured Parcels */}
      {(metadata?.featured_parcels ?? []).length > 0 && (
        <>
          <FeaturedParcels
            parcels={metadata?.featured_parcels ?? []}
            onSelect={onSelectParcel}
          />
          <Divider />
        </>
      )}

      {/* How It Works */}
      <section className="space-y-4">
        <SectionLabel>How it works</SectionLabel>
        <div className="space-y-4">
          {HOW_IT_WORKS.map((item) => (
            <div key={item.step} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center text-sm font-bold text-text-tertiary">
                {item.step}
              </span>
              <div>
                <div className="text-sm font-semibold text-text-primary">
                  {item.title}
                </div>
                <p className="mt-0.5 text-xs leading-relaxed text-text-muted">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <Divider />

      {/* Data Sources */}
      <DataSourcesList metadata={metadata} metadataError={metadataError} />
    </div>
  );
}
