import { formatCurrency, formatPercent } from "@/lib/format";

describe("format utilities", () => {
  it("formats GBP currency values", () => {
    expect(formatCurrency(123.45)).toBe("£123.45");
  });

  it("formats percentages to one decimal place", () => {
    expect(formatPercent(76.666)).toBe("76.7%");
  });
});

