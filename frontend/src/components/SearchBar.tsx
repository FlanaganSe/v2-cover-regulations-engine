/** Search combobox with debounced dropdown results and keyboard navigation. */

import { Search, X } from "lucide-react";
import { useRef, useState } from "react";
import { useParcelSearch } from "../hooks/useParcelSearch";
import type { ParcelSearchResult } from "../types/assessment";

interface SearchBarProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSelect: (result: ParcelSearchResult) => void;
}

export function SearchBar({
  query,
  onQueryChange,
  onSelect,
}: SearchBarProps): React.JSX.Element {
  const { results, isLoading } = useParcelSearch(query);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSelect(result: ParcelSearchResult): void {
    setIsOpen(false);
    setActiveIndex(-1);
    onQueryChange(result.address ?? result.ain);
    onSelect(result);
  }

  function handleClear(): void {
    onQueryChange("");
    setIsOpen(false);
    setActiveIndex(-1);
    inputRef.current?.focus();
  }

  function handleBlur(e: React.FocusEvent): void {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsOpen(false);
      setActiveIndex(-1);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent): void {
    if (!isOpen) return;

    if (e.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
      return;
    }

    if (results.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((i) => (i < results.length - 1 ? i + 1 : 0));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((i) => (i > 0 ? i - 1 : results.length - 1));
        break;
      case "Enter":
        e.preventDefault();
        if (activeIndex >= 0 && activeIndex < results.length) {
          handleSelect(results[activeIndex]);
        }
        break;
    }
  }

  const showDropdown =
    isOpen && (query.trim().length > 0 || results.length > 0);

  return (
    <div className="relative w-full max-w-[480px]" onBlur={handleBlur}>
      <div className="relative">
        <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          aria-controls="search-listbox"
          aria-activedescendant={
            activeIndex >= 0 ? `search-option-${activeIndex}` : undefined
          }
          value={query}
          onChange={(e) => {
            onQueryChange(e.target.value);
            setIsOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search by address or APN..."
          className="w-full rounded-md border border-border-default bg-bg-card py-2 pr-8 pl-9 text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent-primary focus:ring-1 focus:ring-accent-primary focus:outline-none"
        />
        {query && (
          <button
            onClick={handleClear}
            aria-label="Clear search"
            className="absolute top-1/2 right-2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {showDropdown && (
        <div
          id="search-listbox"
          role="listbox"
          className="absolute z-50 mt-1 w-full overflow-hidden rounded-lg border border-border-default bg-bg-card shadow-lg"
        >
          {isLoading && (
            <div className="px-3 py-2.5 text-sm text-text-muted">
              Searching...
            </div>
          )}
          {!isLoading && results.length === 0 && query.trim().length > 0 && (
            <div className="px-3 py-2.5 text-sm text-text-muted">
              No parcels found
            </div>
          )}
          {results.map((result, index) => (
            <button
              key={result.ain}
              id={`search-option-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              onClick={() => handleSelect(result)}
              className={`flex w-full flex-col gap-0.5 px-3 py-2.5 text-left transition-colors ${
                index === activeIndex
                  ? "bg-accent-primary-light"
                  : "hover:bg-bg-hover"
              }`}
            >
              <span className="text-sm font-medium text-text-primary">
                {result.address ?? "No address"}
              </span>
              <span className="flex items-center gap-1.5 text-xs text-text-muted">
                APN {result.apn ?? result.ain}
                {result.zone_class && (
                  <>
                    <span className="text-text-tertiary">&middot;</span>
                    <span className="font-medium text-accent-primary">
                      {result.zone_class}
                    </span>
                  </>
                )}
              </span>
            </button>
          ))}
          {results.length > 0 && (
            <div className="border-t border-border-subtle px-3 py-2 text-xs text-text-tertiary">
              Use arrow keys to navigate, Enter to select
            </div>
          )}
        </div>
      )}
    </div>
  );
}
