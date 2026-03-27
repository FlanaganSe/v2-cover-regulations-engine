import { describe, expect, it } from "vitest";
import { addRecentSearch } from "./recentSearches";

describe("addRecentSearch", () => {
  it("deduplicates entries by AIN and moves the newest to the front", () => {
    const initial = [
      {
        ain: "123",
        apn: "1234-567-890",
        address: "123 Main St",
        zone_class: "R1",
        lastViewedAt: "2026-03-27T00:00:00.000Z",
      },
      {
        ain: "456",
        apn: "9876-543-210",
        address: "456 Oak St",
        zone_class: "R2",
        lastViewedAt: "2026-03-26T00:00:00.000Z",
      },
    ];

    const result = addRecentSearch(initial, {
      ain: "123",
      apn: "1234-567-890",
      address: "123 Main St",
      zone_class: "R1",
    });

    expect(result).toHaveLength(2);
    expect(result[0].ain).toBe("123");
    expect(result[1].ain).toBe("456");
  });

  it("caps recent searches at five entries", () => {
    const initial = Array.from({ length: 5 }, (_, index) => ({
      ain: `${index}`,
      apn: null,
      address: `Parcel ${index}`,
      zone_class: null,
      lastViewedAt: `2026-03-2${index}T00:00:00.000Z`,
    }));

    const result = addRecentSearch(initial, {
      ain: "999",
      apn: null,
      address: "New Parcel",
      zone_class: null,
    });

    expect(result).toHaveLength(5);
    expect(result[0].ain).toBe("999");
    expect(result.some((item) => item.ain === "4")).toBe(false);
  });
});
