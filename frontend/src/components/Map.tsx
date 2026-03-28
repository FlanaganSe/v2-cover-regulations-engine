/** MapLibre GL map with basemap + Martin tile layers. */

import "maplibre-gl/dist/maplibre-gl.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMapGL, {
  type MapLayerMouseEvent,
  type MapRef,
  type ViewStateChangeEvent,
} from "react-map-gl/maplibre";
import { buildMapStyle, PARCEL_INTERACTIVE_LAYER } from "../lib/mapStyle";
import type { ParcelSearchResult } from "../types/assessment";

const LA_CENTER = { longitude: -118.25, latitude: 34.05 };
const INITIAL_ZOOM = 11;

function ainFilter(ain: string): ["==", ["get", string], string] {
  return ["==", ["get", "ain"], ain];
}

const NONE_FILTER = ainFilter("__none__");

interface MapProps {
  selectedLat: number | null;
  selectedLon: number | null;
  selectedAin: string | null;
  onParcelClick?: (result: ParcelSearchResult) => void;
}

export function Map({
  selectedLat,
  selectedLon,
  selectedAin,
  onParcelClick,
}: MapProps): React.JSX.Element {
  const mapRef = useRef<MapRef>(null);
  const [mapStyle] = useState(buildMapStyle);
  const [viewState, setViewState] = useState({
    ...LA_CENTER,
    zoom: INITIAL_ZOOM,
  });
  const hoveredAinRef = useRef<string | null>(null);
  const interactiveLayerIds = useMemo(() => [PARCEL_INTERACTIVE_LAYER], []);

  const handleMove = useCallback((evt: ViewStateChangeEvent) => {
    setViewState(evt.viewState);
  }, []);

  const handleMapError = useCallback((evt: { error?: Error }) => {
    if (evt.error) {
      console.error("MapLibre rendering error", evt.error);
    }
  }, []);

  const setHoverFilter = useCallback((ain: string | null) => {
    const map = mapRef.current?.getMap();
    if (!map || !map.isStyleLoaded()) return;
    const filter = ain ? ainFilter(ain) : NONE_FILTER;
    map.setFilter("parcel-hover-fill", filter);
    map.setFilter("parcel-hover-outline", filter);
    hoveredAinRef.current = ain;
  }, []);

  const handleMouseMove = useCallback(
    (evt: MapLayerMouseEvent) => {
      const feature = evt.features?.[0];
      const ain = (feature?.properties?.ain as string) ?? null;
      if (ain !== hoveredAinRef.current) {
        setHoverFilter(ain);
      }
    },
    [setHoverFilter],
  );

  const handleMouseLeave = useCallback(() => {
    setHoverFilter(null);
  }, [setHoverFilter]);

  const handleClick = useCallback(
    (evt: MapLayerMouseEvent) => {
      const props = evt.features?.[0]?.properties;
      const ain = typeof props?.ain === "string" ? props.ain : undefined;
      if (!ain || !onParcelClick) return;
      onParcelClick({
        ain,
        apn: typeof props?.apn === "string" ? props.apn : null,
        address: typeof props?.address === "string" ? props.address : null,
        zone_class: null,
      });
    },
    [onParcelClick],
  );

  // Fly to selected parcel
  useEffect(() => {
    if (selectedLat != null && selectedLon != null && mapRef.current) {
      mapRef.current.flyTo({
        center: [selectedLon, selectedLat],
        zoom: 17,
        duration: 1500,
      });
    }
  }, [selectedLat, selectedLon]);

  // Highlight selected parcel via feature state
  const prevAinRef = useRef<string | null>(null);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const updateHighlight = (): void => {
      // Clear previous
      if (prevAinRef.current) {
        map.setFilter("selected-parcel-fill", [
          "==",
          ["get", "ain"],
          "__none__",
        ]);
        map.setFilter("selected-parcel-outline", [
          "==",
          ["get", "ain"],
          "__none__",
        ]);
      }

      if (selectedAin) {
        map.setFilter("selected-parcel-fill", [
          "==",
          ["get", "ain"],
          selectedAin,
        ]);
        map.setFilter("selected-parcel-outline", [
          "==",
          ["get", "ain"],
          selectedAin,
        ]);
      }
      prevAinRef.current = selectedAin;
    };

    if (map.isStyleLoaded()) {
      updateHighlight();
    } else {
      map.once("styledata", updateHighlight);
      return () => {
        map.off("styledata", updateHighlight);
      };
    }
  }, [selectedAin]);

  return (
    <ReactMapGL
      ref={mapRef}
      {...viewState}
      onMove={handleMove}
      onError={handleMapError}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      interactiveLayerIds={interactiveLayerIds}
      mapStyle={mapStyle}
      style={{ width: "100%", height: "100%" }}
    />
  );
}
