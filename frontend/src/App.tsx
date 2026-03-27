/** Main app layout: map + search bar + assessment sidebar. */

import { Building2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AssessmentPanel } from "./components/AssessmentPanel";
import { HomePanel } from "./components/HomePanel";
import { Map } from "./components/Map";
import { SearchBar } from "./components/SearchBar";
import { getHomeMetadata, getParcelDetail } from "./lib/api";
import {
  addRecentSearch,
  loadRecentSearches,
  persistRecentSearches,
  type RecentSearchItem,
} from "./lib/recentSearches";
import type { ParcelDetail, ParcelSearchResult } from "./types/assessment";
import type { HomeMetadata } from "./types/home";

type ViewState = "home" | "loading" | "error" | "assessment";

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

    try {
      const data = await getParcelDetail(result.ain);
      if (thisRequest !== requestIdRef.current) return; // stale
      if (!data) {
        setError("Parcel not found.");
        setViewState("error");
        return;
      }
      setDetail(data);
      setViewState("assessment");
      if (data.parcel.center_lat != null && data.parcel.center_lon != null) {
        setSelectedLat(data.parcel.center_lat);
        setSelectedLon(data.parcel.center_lon);
      }

      setRecentSearches((current) =>
        addRecentSearch(current, {
          ain: data.parcel.ain,
          apn: data.parcel.apn,
          address: data.parcel.address,
          zone_class: data.zoning.zone_class,
        }),
      );
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
        <div className="flex-1">
          <Map
            selectedLat={selectedLat}
            selectedLon={selectedLon}
            selectedAin={selectedAin}
          />
        </div>

        {/* Sidebar */}
        <aside className="w-[420px] shrink-0 overflow-y-auto border-l border-border-default bg-bg-sidebar p-6">
          {viewState === "loading" && (
            <div className="flex items-center justify-center py-12 text-sm text-text-muted">
              Loading...
            </div>
          )}
          {viewState === "error" && error && (
            <div className="rounded-lg border border-confidence-low/30 bg-confidence-low-bg p-3 text-sm text-confidence-low">
              {error}
            </div>
          )}
          {viewState === "assessment" && detail && (
            <AssessmentPanel detail={detail} />
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
