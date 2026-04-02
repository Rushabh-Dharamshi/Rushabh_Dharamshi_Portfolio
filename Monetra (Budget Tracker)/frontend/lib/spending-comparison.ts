import { Expense } from "@/lib/types";

export type ComparisonGranularity = "weekly" | "monthly";
export type ComparisonMode = "overall" | "category";

export interface ComparisonPoint {
  label: string;
  value: number;
}

export interface ComparisonSeries {
  label: string;
  shortLabel: string;
  color: string;
  total: number;
  isCurrent: boolean;
  points: ComparisonPoint[];
}

export interface SpendingComparisonModel {
  xLabels: string[];
  categories: string[];
  selectedCategory: string | null;
  series: ComparisonSeries[];
  currentPeriodLabel: string | null;
  strongestPeriodLabel: string | null;
  strongestPeriodValue: number;
  averagePeriodSpend: number;
  currentPeriodChange: number | null;
}

interface BuildOptions {
  granularity: ComparisonGranularity;
  mode: ComparisonMode;
  periodCount: number;
  category?: string;
  referenceDate?: Date;
}

const chartPalette = ["#0f766e", "#2563eb", "#f59e0b", "#b42318", "#7c3aed", "#0891b2", "#3f6212", "#9f1239"];
const weeklyLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const monthlyLabels = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"];

export function buildSpendingComparison(
  expenses: Expense[],
  options: BuildOptions,
): SpendingComparisonModel {
  const referenceDate = options.referenceDate ?? new Date();
  const spendingExpenses = expenses.filter((expense) => (expense.entry_type ?? "expense") === "expense");
  const categories = buildCategoryOptions(spendingExpenses);
  const selectedCategory =
    options.mode === "category"
      ? categories.includes(options.category ?? "") ? options.category ?? null : (categories[0] ?? null)
      : null;
  const filteredExpenses =
    options.mode === "category" && selectedCategory
      ? spendingExpenses.filter((expense) => expense.category === selectedCategory)
      : options.mode === "category"
        ? []
        : spendingExpenses;

  const periods = buildPeriods(options.granularity, options.periodCount, referenceDate);
  const xLabels = options.granularity === "weekly" ? weeklyLabels : monthlyLabels;
  const series = periods.map((period, index) => {
    const buckets = new Array(xLabels.length).fill(0);
    filteredExpenses.forEach((expense) => {
      const expenseDate = parseLocalDate(expense.date);
      if (expenseDate < period.start || expenseDate >= period.endExclusive) {
        return;
      }

      const bucketIndex =
        options.granularity === "weekly"
          ? getWeekdayIndex(expenseDate)
          : Math.min(Math.floor((expenseDate.getDate() - 1) / 7), monthlyLabels.length - 1);
      buckets[bucketIndex] += expense.amount;
    });

    return {
      label: period.label,
      shortLabel: period.shortLabel,
      color: chartPalette[index % chartPalette.length],
      total: roundMoney(buckets.reduce((sum, value) => sum + value, 0)),
      isCurrent: index === periods.length - 1,
      points: xLabels.map((label, bucketIndex) => ({
        label,
        value: roundMoney(buckets[bucketIndex]),
      })),
    };
  });

  const strongestPeriod = series.reduce<ComparisonSeries | null>(
    (currentStrongest, candidate) =>
      currentStrongest === null || candidate.total > currentStrongest.total
        ? candidate
        : currentStrongest,
    null,
  );
  const currentSeries = series.at(-1) ?? null;
  const previousSeries = series.length > 1 ? series[series.length - 2] : null;
  const averagePeriodSpend = series.length
    ? roundMoney(series.reduce((sum, item) => sum + item.total, 0) / series.length)
    : 0;
  const currentPeriodChange =
    previousSeries && previousSeries.total > 0 && currentSeries
      ? roundMoney(((currentSeries.total - previousSeries.total) / previousSeries.total) * 100)
      : null;

  return {
    xLabels,
    categories,
    selectedCategory,
    series,
    currentPeriodLabel: currentSeries?.label ?? null,
    strongestPeriodLabel: strongestPeriod?.label ?? null,
    strongestPeriodValue: strongestPeriod?.total ?? 0,
    averagePeriodSpend,
    currentPeriodChange,
  };
}

function buildCategoryOptions(expenses: Expense[]) {
  const totals = new Map<string, number>();
  expenses.forEach((expense) => {
    totals.set(expense.category, (totals.get(expense.category) ?? 0) + expense.amount);
  });
  return Array.from(totals.entries())
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([category]) => category);
}

function buildPeriods(
  granularity: ComparisonGranularity,
  periodCount: number,
  referenceDate: Date,
) {
  const safeCount = granularity === "weekly"
    ? clamp(periodCount, 2, 8)
    : clamp(periodCount, 2, 6);
  const periods = [];

  if (granularity === "weekly") {
    const currentPeriodStart = startOfWeek(referenceDate);
    for (let index = safeCount - 1; index >= 0; index -= 1) {
      const start = addDays(currentPeriodStart, -7 * index);
      const endExclusive = addDays(start, 7);
      periods.push({
        start,
        endExclusive,
        label: `${formatShortDate(start)} - ${formatShortDate(addDays(endExclusive, -1))}`,
        shortLabel: index === 0 ? "Current week" : `${index}w ago`,
      });
    }
    return periods;
  }

  const currentPeriodStart = new Date(referenceDate.getFullYear(), referenceDate.getMonth(), 1);
  for (let index = safeCount - 1; index >= 0; index -= 1) {
    const start = addMonths(currentPeriodStart, -index);
    const endExclusive = addMonths(start, 1);
    periods.push({
      start,
      endExclusive,
      label: start.toLocaleString("en-GB", { month: "long", year: "numeric" }),
      shortLabel: start.toLocaleString("en-GB", { month: "short" }),
    });
  }
  return periods;
}

function parseLocalDate(rawDate: string) {
  const [year, month, day] = rawDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function startOfWeek(referenceDate: Date) {
  const clone = new Date(referenceDate.getFullYear(), referenceDate.getMonth(), referenceDate.getDate());
  const offset = (clone.getDay() + 6) % 7;
  clone.setDate(clone.getDate() - offset);
  return clone;
}

function addDays(referenceDate: Date, days: number) {
  const clone = new Date(referenceDate);
  clone.setDate(clone.getDate() + days);
  return clone;
}

function addMonths(referenceDate: Date, months: number) {
  return new Date(referenceDate.getFullYear(), referenceDate.getMonth() + months, 1);
}

function getWeekdayIndex(referenceDate: Date) {
  return (referenceDate.getDay() + 6) % 7;
}

function formatShortDate(referenceDate: Date) {
  return referenceDate.toLocaleString("en-GB", { day: "2-digit", month: "short" });
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function roundMoney(value: number) {
  return Math.round(value * 100) / 100;
}
