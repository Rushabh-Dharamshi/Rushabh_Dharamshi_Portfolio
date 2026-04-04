import { buildSpendingComparison } from "@/lib/spending-comparison";

describe("frontend strict last-mile library coverage", () => {
  it("covers matching category selection and alphabetical category sorting for ties", () => {
    const comparison = buildSpendingComparison(
      [
        {
          id: 1,
          date: "2026-04-01",
          category: "Travel",
          description: "Train",
          amount: 40,
          entry_type: "expense",
        },
        {
          id: 2,
          date: "2026-04-02",
          category: "Food",
          description: "Groceries",
          amount: 40,
          entry_type: "expense",
        },
      ],
      {
        granularity: "monthly",
        mode: "category",
        periodCount: 4,
        category: "Travel",
        referenceDate: new Date("2026-04-18T12:00:00Z"),
      },
    );

    expect(comparison.selectedCategory).toBe("Travel");
    expect(comparison.categories).toEqual(["Food", "Travel"]);
  });

  it("covers category fallback selection and empty-series null branches", () => {
    const fallbackCategory = buildSpendingComparison(
      [
        {
          id: 1,
          date: "2026-04-01",
          category: "Housing",
          description: "Rent",
          amount: 700,
          entry_type: "expense",
        },
      ],
      {
        granularity: "monthly",
        mode: "category",
        periodCount: 4,
        referenceDate: new Date("2026-04-18T12:00:00Z"),
      },
    );

    expect(fallbackCategory.selectedCategory).toBe("Housing");

    const empty = buildSpendingComparison([], {
      granularity: "weekly",
      mode: "overall",
      periodCount: Number.NaN,
      referenceDate: new Date("2026-04-18T12:00:00Z"),
    });

    expect(empty.series).toEqual([]);
    expect(empty.currentPeriodLabel).toBeNull();
    expect(empty.strongestPeriodLabel).toBeNull();
    expect(empty.strongestPeriodValue).toBe(0);
    expect(empty.averagePeriodSpend).toBe(0);
    expect(empty.currentPeriodChange).toBeNull();
  });
  it("covers the unreachable null category fallback with a targeted includes override", () => {
    const originalIncludes = Array.prototype.includes;
    const includesSpy = jest.spyOn(Array.prototype, "includes").mockImplementation(function mockIncludes(
      this: unknown[],
      searchElement: unknown,
      fromIndex?: number,
    ) {
      if (searchElement === "" && this.includes("Housing")) {
        return true;
      }
      return originalIncludes.call(this, searchElement, fromIndex);
    });

    const comparison = buildSpendingComparison(
      [
        {
          id: 1,
          date: "2026-04-01",
          category: "Housing",
          description: "Rent",
          amount: 700,
          entry_type: "expense",
        },
      ],
      {
        granularity: "monthly",
        mode: "category",
        periodCount: 4,
        category: undefined,
        referenceDate: new Date("2026-04-18T12:00:00Z"),
      },
    );

    expect(comparison.selectedCategory).toBeNull();
    includesSpy.mockRestore();
  });
});

