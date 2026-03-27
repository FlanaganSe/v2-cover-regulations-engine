/** Basemap + Martin tile source config. */

import type { StyleSpecification } from "maplibre-gl";

const MARTIN_URL = import.meta.env.VITE_MARTIN_URL ?? "http://localhost:3001";
const BASEMAP_TILE_URL =
  import.meta.env.VITE_BASEMAP_TILE_URL ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const BASEMAP_ATTRIBUTION =
  import.meta.env.VITE_BASEMAP_ATTRIBUTION ??
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/** Color map for zone classes. */
const ZONE_COLORS: Record<string, string> = {
  R1: "#4CAF50",
  RS: "#66BB6A",
  R2: "#8BC34A",
  R3: "#FF9800",
  R4: "#F44336",
  R5: "#9C27B0",
  RA: "#81C784",
  RE9: "#81C784",
  RE11: "#81C784",
  RE15: "#81C784",
  RE20: "#81C784",
  RE40: "#81C784",
  RD1: "#FFB74D",
  RD2: "#FFB74D",
  RD3: "#FFB74D",
  RD4: "#FFB74D",
  RD5: "#FFB74D",
  RD6: "#FFB74D",
  RW1: "#AB47BC",
  RW2: "#AB47BC",
  RMP: "#78909C",
  RU: "#78909C",
};

const DEFAULT_ZONE_COLOR = "#9E9E9E";

/** Build the zone color match expression for MapLibre. */
function buildZoneColorExpression(): (string | string[])[] {
  const expr: (string | string[])[] = ["match", ["get", "zone_class"]];
  for (const [zone, color] of Object.entries(ZONE_COLORS)) {
    expr.push(zone, color);
  }
  expr.push(DEFAULT_ZONE_COLOR);
  return expr;
}

export function buildMapStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles: [BASEMAP_TILE_URL],
        tileSize: 256,
        maxzoom: 19,
        attribution: BASEMAP_ATTRIBUTION,
      },
      zoning: {
        type: "vector",
        url: `${MARTIN_URL}/zoning`,
      },
      buildings: {
        type: "vector",
        url: `${MARTIN_URL}/buildings`,
      },
      parcels: {
        type: "vector",
        url: `${MARTIN_URL}/parcels`,
      },
    },
    layers: [
      {
        id: "basemap",
        type: "raster",
        source: "basemap",
      },
      {
        id: "zoning-fill",
        type: "fill",
        source: "zoning",
        "source-layer": "zoning",
        paint: {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          "fill-color": buildZoneColorExpression() as any,
          "fill-opacity": 0.25,
        },
        minzoom: 13,
      },
      {
        id: "zoning-outline",
        type: "line",
        source: "zoning",
        "source-layer": "zoning",
        paint: {
          "line-color": "#666",
          "line-width": 0.5,
        },
        minzoom: 13,
      },
      {
        id: "buildings-fill",
        type: "fill",
        source: "buildings",
        "source-layer": "buildings",
        paint: {
          "fill-color": "#9E9E9E",
          "fill-opacity": 0.3,
        },
        minzoom: 15,
      },
      {
        id: "buildings-outline",
        type: "line",
        source: "buildings",
        "source-layer": "buildings",
        paint: {
          "line-color": "#757575",
          "line-width": 0.5,
        },
        minzoom: 15,
      },
      {
        id: "selected-parcel-fill",
        type: "fill",
        source: "parcels",
        "source-layer": "parcels",
        filter: ["==", ["get", "ain"], "__none__"],
        paint: {
          "fill-color": "#2196F3",
          "fill-opacity": 0.3,
        },
      },
      {
        id: "selected-parcel-outline",
        type: "line",
        source: "parcels",
        "source-layer": "parcels",
        filter: ["==", ["get", "ain"], "__none__"],
        paint: {
          "line-color": "#1565C0",
          "line-width": 3,
        },
      },
    ],
  };
}

export { BASEMAP_ATTRIBUTION, BASEMAP_TILE_URL, MARTIN_URL };
