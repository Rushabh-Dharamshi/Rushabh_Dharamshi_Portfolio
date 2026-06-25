import { formatBackendTimestamp } from "@/lib/date-time";

describe("formatBackendTimestamp", () => {
  it("treats timezone-less backend timestamps as UTC", () => {
    const formatted = formatBackendTimestamp("2026-05-04T17:38:00");
    const expected = new Date("2026-05-04T17:38:00Z").toLocaleString("en-GB", { timeZone: "Europe/London" });

    expect(formatted).toBe(expected);
  });

  it("passes invalid timestamps through", () => {
    expect(formatBackendTimestamp("not-a-date")).toBe("not-a-date");
  });

  it("handles missing timestamps", () => {
    expect(formatBackendTimestamp(null)).toBe("Not available");
  });
});
