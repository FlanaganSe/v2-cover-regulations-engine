/** MapLibre GL map with basemap + Martin tile layers. */

import "maplibre-gl/dist/maplibre-gl.css";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMapGL, {
  type MapRef,
  type ViewStateChangeEvent,
} from "react-map-gl/maplibre";
import { buildMapStyle } from "../lib/mapStyle";

const LA_CENTER = { longitude: -118.25, latitude: 34.05 };
const INITIAL_ZOOM = 11;

interface MapProps {
  selectedLat: number | null;
  selectedLon: number | null;
  selectedAin: string | null;
}

export function Map({
  selectedLat,
  selectedLon,
  selectedAin,
}: MapProps): React.JSX.Element {
  const mapRef = useRef<MapRef>(null);
  const [mapStyle] = useState(buildMapStyle);
  const [viewState, setViewState] = useState({
    ...LA_CENTER,
    zoom: INITIAL_ZOOM,
  });

  const handleMove = useCallback((evt: ViewStateChangeEvent) => {
    setViewState(evt.viewState);
  }, []);

  const handleMapError = useCallback((evt: { error?: Error }) => {
    if (evt.error) {
      console.error("MapLibre rendering error", evt.error);
    }
  }, []);

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
      mapStyle={mapStyle}
      style={{ width: "100%", height: "100%" }}
    >
      {/* Selected parcel highlight layers are added inline via style */}
    </ReactMapGL>
  );
}
