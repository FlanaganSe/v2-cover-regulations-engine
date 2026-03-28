/** Main app layout: map + search bar + assessment sidebar. */

import { Building2, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AssessmentPanel } from "./components/AssessmentPanel";
import { HomePanel } from "./components/HomePanel";
import { Map } from "./components/Map";
import { SearchBar } from "./components/SearchBar";
import {
  getHomeMetadata,
  getParcelAssessment,
  getParcelFacts,
} from "./lib/api";
import {
  addRecentSearch,
  loadRecentSearches,
  persistRecentSearches,
  type RecentSearchItem,
} from "./lib/recentSearches";
import type { ParcelDetail, ParcelSearchResult } from "./types/assessment";
import type { HomeMetadata } from "./types/home";

type ViewState = "home" | "loading" | "error" | "assessment";

const ZONE_LEGEND = [
  { label: "R1 / RS", color: "#4CAF50" },
  { label: "R3 / RD", color: "#FF9800" },
  { label: "R4 / R5", color: "#F44336" },
  { label: "RE / RA", color: "#81C784" },
] as const;

function ZoneLegend(): React.JSX.Element {
  return (
    <div className="absolute bottom-4 left-4 z-10 rounded-lg border border-border-default bg-bg-card/90 px-3 py-2.5 shadow-card backdrop-blur-sm">
      <p className="mb-1.5 text-[10px] font-semibold tracking-widest text-text-muted uppercase">
        Zone overlay
      </p>
      <div className="space-y-1">
        {ZONE_LEGEND.map(({ label, color }) => (
          <div key={label} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[11px] text-text-secondary">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function App(): React.JSX.Element {
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState<ParcelDetail | null>(null);
  const [viewState, setViewState] = useState<ViewState>("home");
  const [error, setError] = useState<string | null>(null);
  const [selectedLat, setSelectedLat] = useState<number | null>(null);
  const [selectedLon, setSelectedLon] = useState<number | null>(null);
  const [selectedAin, setSelectedAin] = useState<string | null>(null);
  const [homeMetadata, setHomeMetadata] = useState<HomeMetadata | null>(null);
  const [homeMetadataError, setHomeMetadataError] = useState(false);
  const [recentSearches, setRecentSearches] = useState<RecentSearchItem[]>(() =>
    loadRecentSearches(),
  );
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const requestIdRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    getHomeMetadata()
      .then((data) => {
        if (cancelled) return;
        setHomeMetadata(data);
        setHomeMetadataError(false);
      })
      .catch(() => {
        if (cancelled) return;
        setHomeMetadataError(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    persistRecentSearches(recentSearches);
  }, [recentSearches]);

  const resetToHome = useCallback(() => {
    requestIdRef.current += 1;
    setQuery("");
    setDetail(null);
    setError(null);
    setSelectedAin(null);
    setSelectedLat(null);
    setSelectedLon(null);
    setViewState("home");
  }, []);

  const handleSelect = useCallback(async (result: ParcelSearchResult) => {
    const thisRequest = ++requestIdRef.current;
    setQuery(result.address ?? result.ain);
    setSelectedAin(result.ain);
    setViewState("loading");
    setError(null);
    setDetail(null);
    setAssessmentLoading(false);

    try {
      // Phase 1: fast deterministic data (~200ms)
      const facts = await getParcelFacts(result.ain);
      if (thisRequest !== requestIdRef.current) return; // stale
      if (!facts) {
        setError("Parcel not found.");
        setViewState("error");
        return;
      }
      setDetail(facts);
      setViewState("assessment");
      setAssessmentLoading(true);
      if (facts.parcel.center_lat != null && facts.parcel.center_lon != null) {
        setSelectedLat(facts.parcel.center_lat);
        setSelectedLon(facts.parcel.center_lon);
      }

      setRecentSearches((current) =>
        addRecentSearch(current, {
          ain: facts.parcel.ain,
          apn: facts.parcel.apn,
          address: facts.parcel.address,
          zone_class: facts.zoning.zone_class,
        }),
      );

      // Phase 2: LLM assessment (2-5s, non-critical)
      try {
        const llmAssessment = await getParcelAssessment(result.ain);
        if (thisRequest !== requestIdRef.current) return; // stale
        if (llmAssessment) {
          setDetail((prev) =>
            prev ? { ...prev, assessment: llmAssessment } : prev,
          );
        }
      } catch {
        // LLM failure is non-critical; deterministic assessment remains
      } finally {
        if (thisRequest === requestIdRef.current) {
          setAssessmentLoading(false);
        }
      }
    } catch {
      if (thisRequest !== requestIdRef.current) return; // stale
      setError("Failed to load parcel details.");
      setViewState("error");
    }
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-bg-page">
      {/* Header */}
      <header className="flex h-14 shrink-0 items-center border-b border-border-default bg-bg-card px-4 md:px-6">
        {/* Logo / Brand — left */}
        <button
          onClick={resetToHome}
          aria-label="Home"
          title="Home"
          className="flex shrink-0 items-center gap-2 transition-opacity hover:opacity-80"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-primary">
            <Building2 className="h-4 w-4 text-white" />
          </div>
          <div className="hidden items-baseline gap-1.5 sm:flex">
            <span className="text-sm font-semibold text-text-primary">
              Regulation Engine
            </span>
            <span className="hidden text-xs font-medium text-text-tertiary md:inline">
              Los Angeles Zoning
            </span>
          </div>
        </button>

        {/* Search — centered */}
        <div className="mx-4 flex min-w-0 flex-1 justify-center">
          <SearchBar
            query={query}
            onQueryChange={setQuery}
            onSelect={handleSelect}
          />
        </div>

        {/* Keyboard shortcut hint — right */}
        <div className="hidden shrink-0 sm:block">
          <kbd
            aria-hidden="true"
            className="rounded-md border border-border-default bg-bg-muted px-1.5 py-0.5 text-xs font-medium text-text-muted"
          >
            ⌘K
          </kbd>
        </div>
      </header>

      {/* Main content: map + sidebar */}
      <div className="flex min-h-0 flex-1">
        {/* Map */}
        <div className="relative flex-1">
          <Map
            selectedLat={selectedLat}
            selectedLon={selectedLon}
            selectedAin={selectedAin}
          />
          <ZoneLegend />
        </div>

        {/* Sidebar — 420px on home, 480px on detail */}
        <aside
          className={`shrink-0 overflow-y-auto border-l border-border-default bg-bg-sidebar p-6 transition-[width] duration-200 ease-in-out ${
            viewState === "home" ? "w-[420px]" : "w-[480px]"
          }`}
        >
          {viewState === "loading" && (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading...
            </div>
          )}
          {viewState === "error" && error && (
            <div className="rounded-lg border border-confidence-low/30 bg-confidence-low-bg p-3 text-sm text-confidence-low">
              {error}
            </div>
          )}
          {viewState === "assessment" && detail && (
            <AssessmentPanel
              detail={detail}
              assessmentLoading={assessmentLoading}
            />
          )}
          {viewState === "home" && (
            <HomePanel
              metadata={homeMetadata}
              metadataError={homeMetadataError}
              recentSearches={recentSearches}
              onSelectParcel={handleSelect}
            />
          )}
        </aside>
      </div>
    </div>
  );
}
