/** Main app layout: map + search bar + assessment sidebar. */

import { useCallback, useRef, useState } from "react";
import { AssessmentPanel } from "./components/AssessmentPanel";
import { Map } from "./components/Map";
import { SearchBar } from "./components/SearchBar";
import { getParcelDetail } from "./lib/api";
import type { ParcelDetail, ParcelSearchResult } from "./types/assessment";

export function App(): React.JSX.Element {
  const [detail, setDetail] = useState<ParcelDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedLat, setSelectedLat] = useState<number | null>(null);
  const [selectedLon, setSelectedLon] = useState<number | null>(null);
  const [selectedAin, setSelectedAin] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const handleSelect = useCallback(async (result: ParcelSearchResult) => {
    const thisRequest = ++requestIdRef.current;
    setSelectedAin(result.ain);
    setIsLoading(true);
    setError(null);
    setDetail(null);

    try {
      const data = await getParcelDetail(result.ain);
      if (thisRequest !== requestIdRef.current) return; // stale
      if (!data) {
        setError("Parcel not found.");
        return;
      }
      setDetail(data);
      if (data.parcel.center_lat != null && data.parcel.center_lon != null) {
        setSelectedLat(data.parcel.center_lat);
        setSelectedLon(data.parcel.center_lon);
      }
    } catch {
      if (thisRequest !== requestIdRef.current) return; // stale
      setError("Failed to load parcel details.");
    } finally {
      if (thisRequest === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-gray-50">
      {/* Header with search */}
      <header className="flex items-center gap-4 border-b border-gray-200 bg-white px-4 py-2 shadow-sm">
        <h1 className="shrink-0 text-lg font-semibold text-gray-800">
          LA Zoning
        </h1>
        <SearchBar onSelect={handleSelect} />
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
          {isLoading && (
            <div className="flex items-center justify-center py-12 text-sm text-gray-500">
              Loading...
            </div>
          )}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
          {!isLoading && !error && detail && (
            <AssessmentPanel detail={detail} />
          )}
          {!isLoading && !error && !detail && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-sm text-gray-500">
                Search for an address or APN to see zoning details.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
