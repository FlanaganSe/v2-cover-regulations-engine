import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { ParcelDetail } from "./types/assessment";
import type { HomeMetadata } from "./types/home";

vi.mock("./components/Map", () => ({
  Map: () => <div data-testid="mock-map">Map</div>,
}));

const homeMetadataFixture: HomeMetadata = {
  data_as_of: "2026-03-27T12:00:00Z",
  supported_zone_classes: ["R1", "R2", "R3"],
  sources: [
    {
      id: "parcels",
      label: "LA County Parcels",
      source_url: "https://example.com/parcels",
      coverage_note: "Parcel geometry and address coverage.",
    },
  ],
  featured_parcels: [
    {
      category: "clean_supported",
      label: "Clean supported parcel",
      description: "A straightforward supported example.",
      ain: "1234567890",
      apn: "1234-567-890",
      address: "123 Main St",
      zone_class: "R1",
    },
  ],
};

const parcelDetailFixture: ParcelDetail = {
  parcel: {
    ain: "1234567890",
    apn: "1234-567-890",
    address: "123 Main St",
    center_lat: 34.05,
    center_lon: -118.25,
    lot_sqft: 5000,
    year_built: 1950,
    use_description: "Single Family Residence",
    bedrooms: 3,
    sqft_main: 1600,
  },
  scope: {
    in_la_city: true,
    supported_zone: true,
    chapter_1a: false,
  },
  zoning: {
    zone_string: "R1-1",
    zone_class: "R1",
    height_district: "1",
    q_flag: false,
    d_flag: false,
    t_flag: false,
    suffixes: [],
  },
  overlays: {
    specific_plan: null,
    hpoz: null,
    community_plan: "Silver Lake - Echo Park",
    general_plan_lu: "Low I Residential",
  },
  standards: {
    height_ft: 33,
    stories: 2,
    far_or_rfa: 0.45,
    far_type: "RFA",
    front_setback_ft: "20%≤20",
    side_setback_ft: "5",
    rear_setback_ft: "15",
    density_description: "1 per lot",
    allowed_uses: ["Single-family", "ADU"],
  },
  adu: {
    allowed: true,
    max_sqft: 1200,
    setbacks_ft: 4,
    notes: "ADU likely allowed.",
  },
  confidence: {
    level: "High",
    reasons: ["Supported residential zone with no modifiers"],
  },
  assessment: {
    summary: "This parcel is zoned R1-1 and supports a single-family home.",
    citations: ["LAMC §12.08"],
    caveats: ["Informational purposes only."],
    llm_available: false,
  },
  metadata: {
    data_as_of: "2026-03-27T12:00:00Z",
    source_urls: ["https://example.com/parcels"],
  },
};

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("App homepage flow", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    fetchMock.mockReset();
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("renders the home panel with live metadata", async () => {
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/home")) {
        return jsonResponse(homeMetadataFixture);
      }
      if (url.includes("/api/parcels/search")) {
        return jsonResponse([]);
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: /Understand what can be confidently built on a parcel/i,
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Featured parcels")).toBeInTheDocument();
    expect(
      await screen.findByText(/Latest data snapshot:/i),
    ).toBeInTheDocument();
    expect(await screen.findByText("LA County Parcels")).toBeInTheDocument();
  });

  it("keeps static guidance visible when homepage metadata fails", async () => {
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/home")) {
        throw new Error("metadata unavailable");
      }
      if (url.includes("/api/parcels/search")) {
        return jsonResponse([]);
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: /Understand what can be confidently built on a parcel/i,
      }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/Live source metadata could not be loaded/i),
    ).toBeInTheDocument();
    expect(await screen.findByText("ZIMAS")).toBeInTheDocument();
  });

  it("loads a featured parcel into the assessment view and returns home", async () => {
    const user = userEvent.setup();

    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/home")) {
        return jsonResponse(homeMetadataFixture);
      }
      if (url.includes("/api/parcels/search")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/api/parcels/1234567890")) {
        return jsonResponse(parcelDetailFixture);
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /clean supported parcel/i }),
    );

    expect(await screen.findByText("Summary")).toBeInTheDocument();
    expect(
      await screen.findByText(parcelDetailFixture.assessment.summary),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^home$/i }));

    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: /Understand what can be confidently built on a parcel/i,
      }),
    ).toBeInTheDocument();
  });

  it("renders recent searches from localStorage and reopens one", async () => {
    const user = userEvent.setup();

    window.localStorage.setItem(
      "recentParcelSearches",
      JSON.stringify([
        {
          ain: "1234567890",
          apn: "1234-567-890",
          address: "123 Main St",
          zone_class: "R1",
          lastViewedAt: "2026-03-27T12:00:00.000Z",
        },
      ]),
    );

    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/home")) {
        return jsonResponse({ ...homeMetadataFixture, featured_parcels: [] });
      }
      if (url.includes("/api/parcels/search")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/api/parcels/1234567890")) {
        return jsonResponse(parcelDetailFixture);
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /123 main st/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByText(parcelDetailFixture.assessment.summary),
      ).toBeInTheDocument();
    });
  });
});
