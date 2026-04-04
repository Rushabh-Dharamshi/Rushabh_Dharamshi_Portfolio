describe("frontend strict isolate branches", () => {
  afterEach(() => {
    jest.resetModules();
    jest.restoreAllMocks();
    jest.dontMock("@/lib/spending-comparison");
  });

  it("covers spending-comparison empty-summary and category-select branches", () => {
    let renderLocal: typeof import("@testing-library/react").render;
    let fireEventLocal: typeof import("@testing-library/react").fireEvent;
    let screenLocal: typeof import("@testing-library/react").screen;
    let ReactLocal: typeof import("react");
    let SpendingComparisonPanel: any;

    jest.isolateModules(() => {
      jest.doMock("@/lib/spending-comparison", () => ({
        buildSpendingComparison: (_expenses: unknown[], options: { mode: string; category?: string }) =>
          options.mode === "category"
            ? {
                xLabels: ["Mon"],
                categories: ["Food", "Travel"],
                selectedCategory: options.category || "Food",
                series: [
                  {
                    label: "April 2026",
                    shortLabel: "Apr",
                    color: "#0f766e",
                    total: 10,
                    isCurrent: true,
                    points: [{ label: "Mon", value: 10 }],
                  },
                ],
                currentPeriodLabel: "April 2026",
                strongestPeriodLabel: "April 2026",
                strongestPeriodValue: 10,
                averagePeriodSpend: 10,
                currentPeriodChange: 0,
              }
            : {
                xLabels: [],
                categories: [],
                selectedCategory: null,
                series: [],
                currentPeriodLabel: null,
                strongestPeriodLabel: null,
                strongestPeriodValue: 0,
                averagePeriodSpend: 0,
                currentPeriodChange: null,
              },
      }));

      ReactLocal = require("react");
      ({ render: renderLocal, fireEvent: fireEventLocal, screen: screenLocal } = require("@testing-library/react/pure"));
      SpendingComparisonPanel = require("@/components/spending-comparison-panel").SpendingComparisonPanel;
    });

    renderLocal(
      ReactLocal.createElement(SpendingComparisonPanel, {
        expenses: [],
        referenceDate: new Date("2026-04-18T12:00:00Z"),
      }),
    );

    expect(screenLocal.getAllByText("No data").length).toBeGreaterThan(0);
    expect(
      screenLocal.getByText("Comparison lines will appear once spending transactions are available."),
    ).toBeInTheDocument();

    fireEventLocal.click(screenLocal.getByRole("button", { name: "Category" }));
    const select = screenLocal.getByRole("combobox");
    fireEventLocal.change(select, { target: { value: "Travel" } });
    expect(select).toHaveValue("Travel");
  });

  it("covers the recurring nullish end-date branch via a state override", () => {
    let renderLocal: typeof import("@testing-library/react").render;
    let screenLocal: typeof import("@testing-library/react").screen;
    let ReactLocal: typeof import("react");
    let RecurringCalendarPanel: any;

    jest.isolateModules(() => {
      ReactLocal = require("react");
      const reactModule = require("react");
      const realUseState = jest.requireActual("react").useState;
      let callCount = 0;
      jest.spyOn(reactModule, "useState").mockImplementation((initial: unknown) => {
        callCount += 1;
        if (callCount === 1) {
          return realUseState({ ...(initial as Record<string, unknown>), end_date: undefined });
        }
        return realUseState(initial);
      });

      ({ render: renderLocal, screen: screenLocal } = require("@testing-library/react/pure"));
      RecurringCalendarPanel = require("@/components/recurring-calendar-panel").RecurringCalendarPanel;
    });

    renderLocal(
      ReactLocal.createElement(RecurringCalendarPanel, {
        items: [],
        calendar: {
          window_start: "2026-04-01",
          window_end: "2026-05-06",
          occurrences: [],
          completed_occurrences: [],
        },
        onCreate: jest.fn(),
        onUpdate: jest.fn(),
        onDelete: jest.fn(),
        onMarkPaid: jest.fn(),
        onMarkUnpaid: jest.fn(),
      }),
    );

    expect(screenLocal.getByLabelText("End date (optional)")).toHaveValue("");
  });
});

