/** Main app layout: map + search bar + assessment sidebar. */

import { Home } from "lucide-react";
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
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-gray-50">
      {/* Header with search */}
      <header className="flex items-center gap-4 border-b border-gray-200 bg-white px-4 py-2 shadow-sm">
        <button
          onClick={resetToHome}
          className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
        >
          <Home className="h-4 w-4" />
          Home
        </button>
        <h1 className="shrink-0 text-lg font-semibold text-gray-800">
          LA Zoning
        </h1>
        <SearchBar
          query={query}
          onQueryChange={setQuery}
          onSelect={handleSelect}
        />
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

        {/* Assessment sidebar */}
        <aside className="w-96 shrink-0 overflow-y-auto border-l border-gray-200 bg-gray-50 p-4">
          {viewState === "loading" && (
            <div className="flex items-center justify-center py-12 text-sm text-gray-500">
              Loading...
            </div>
          )}
          {viewState === "error" && error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
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
