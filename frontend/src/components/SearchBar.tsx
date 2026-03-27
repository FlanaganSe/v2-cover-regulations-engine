/** Search combobox with debounced dropdown results. */

import { Search, X } from "lucide-react";
import { useRef, useState } from "react";
import { useParcelSearch } from "../hooks/useParcelSearch";
import type { ParcelSearchResult } from "../types/assessment";

interface SearchBarProps {
  onSelect: (result: ParcelSearchResult) => void;
}

export function SearchBar({ onSelect }: SearchBarProps): React.JSX.Element {
  const { query, setQuery, results, isLoading } = useParcelSearch();
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSelect(result: ParcelSearchResult): void {
    setIsOpen(false);
    setQuery(result.address ?? result.ain);
    onSelect(result);
  }

  function handleClear(): void {
    setQuery("");
    setIsOpen(false);
    inputRef.current?.focus();
  }

  return (
    <div className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          placeholder="Search address or APN..."
          className="w-full rounded-lg border border-gray-300 bg-white py-2 pr-8 pl-9 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute top-1/2 right-2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {isOpen && (query.trim().length > 0 || results.length > 0) && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg">
          {isLoading && (
            <div className="px-3 py-2 text-sm text-gray-500">Searching...</div>
          )}
          {!isLoading && results.length === 0 && query.trim().length > 0 && (
            <div className="px-3 py-2 text-sm text-gray-500">
              No parcels found
            </div>
          )}
          {results.map((result) => (
            <button
              key={result.ain}
              onClick={() => handleSelect(result)}
              className="flex w-full flex-col px-3 py-2 text-left hover:bg-blue-50"
            >
              <span className="text-sm font-medium text-gray-900">
                {result.address ?? "No address"}
              </span>
              <span className="text-xs text-gray-500">
                APN: {result.apn ?? result.ain}
                {result.zone_class && ` · ${result.zone_class}`}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Close dropdown on outside click */}
      {isOpen && (
        <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
      )}
    </div>
  );
}
