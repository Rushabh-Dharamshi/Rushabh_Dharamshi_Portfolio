import calendar
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from budget_tracker_api.repositories.expense_repository import ExpenseRepository
from budget_tracker_api.schemas import Expense


@dataclass(slots=True)
class ReportContext:
    report_month_key: str
    previous_month_key: str
    report_month_label: str
    previous_month_label: str
    monthly_budget: float
    current_total: float
    previous_total: float
    current_income_total: float
    previous_income_total: float
    current_net_cash_flow: float
    previous_net_cash_flow: float
    remaining_budget: float
    budget_variance: float
    month_over_month_change: float
    budget_utilization: float
    income_coverage_ratio: float
    transaction_count: int
    average_transaction: float
    average_daily_spend: float
    projected_month_end_spend: float
    largest_transaction: Expense | None
    top_category: str | None
    top_category_share: float
    daily_totals: list[tuple[str, float]]
    monthly_trend: list[tuple[str, float]]
    monthly_cash_flow_trend: list[dict]
    category_rows: list[dict]
    largest_expenses: list[Expense]
    insights: list[str]
    recommendations: list[str]


class ReportService:
    def __init__(
        self,
        repository: ExpenseRepository,
        budget_provider: Callable[[str | None], float],
        income_provider: Callable[[str | None], float],
        output_dir: Path,
    ):
        self._repository = repository
        self._budget_provider = budget_provider
        self._income_provider = income_provider
        self._output_dir = output_dir

    def generate_monthly_report(self, month_key: str | None = None) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        report_date = self._resolve_report_date(month_key, now)
        context = self._build_context(report_date, generated_at=now)
        chart_paths = [
            self._create_category_comparison_chart(context),
            self._create_daily_spending_chart(context),
            self._create_monthly_trend_chart(context),
            self._create_cash_flow_chart(context),
        ]

        pdf_path = self._output_dir / f"Monthly_Budget_Report_{report_date.strftime('%B_%Y')}.pdf"
        document = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.65 * inch,
            bottomMargin=0.65 * inch,
        )

        try:
            story = self._build_story(context, chart_paths)
            document.build(
                story,
                onFirstPage=self._decorate_page,
                onLaterPages=self._decorate_page,
            )
        finally:
            for path in chart_paths:
                if path and path.exists():
                    path.unlink()

        return pdf_path

    @staticmethod
    def _resolve_report_date(month_key: str | None, now: datetime) -> datetime:
        if not month_key:
            return now
        return datetime.strptime(str(month_key), "%Y-%m")

    def _build_context(self, now: datetime, generated_at: datetime | None = None) -> ReportContext:
        generated_at = generated_at or datetime.now()
        report_month_key = now.strftime("%Y-%m")
        previous_month_date = now.replace(day=1) - timedelta(days=1)
        previous_month_key = previous_month_date.strftime("%Y-%m")
        monthly_budget = self._budget_provider(report_month_key)

        report_expenses = self._repository.expenses_for_month(report_month_key, "expense")
        previous_expenses = self._repository.expenses_for_month(previous_month_key, "expense")
        current_total = round(sum(expense.amount for expense in report_expenses), 2)
        previous_total = round(sum(expense.amount for expense in previous_expenses), 2)
        current_income_total = self._repository.monthly_total(report_month_key, "income")
        if current_income_total <= 0:
            current_income_total = round(self._income_provider(report_month_key), 2)
        previous_income_total = self._repository.monthly_total(previous_month_key, "income")
        if previous_income_total <= 0:
            previous_income_total = round(self._income_provider(previous_month_key), 2)
        current_net_cash_flow = round(current_income_total - current_total, 2)
        previous_net_cash_flow = round(previous_income_total - previous_total, 2)
        transaction_count = len(report_expenses)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_elapsed = max(now.day, 1) if now.strftime("%Y-%m") == generated_at.strftime("%Y-%m") else days_in_month
        average_transaction = round(current_total / transaction_count, 2) if transaction_count else 0.0
        average_daily_spend = round(current_total / days_elapsed, 2) if current_total else 0.0
        projected_month_end_spend = round(average_daily_spend * days_in_month, 2)
        remaining_budget = round(monthly_budget - current_total, 2)
        budget_variance = round(current_total - monthly_budget, 2)
        month_over_month_change = round(current_total - previous_total, 2)
        budget_utilization = round((current_total / monthly_budget) * 100, 2) if monthly_budget else 0.0
        income_coverage_ratio = round((current_income_total / current_total) * 100, 2) if current_total else 0.0

        category_rows = self._build_category_rows(report_month_key, previous_month_key, current_total, report_expenses)
        largest_expenses = self._repository.largest_expenses(report_month_key, limit=8)
        largest_transaction = largest_expenses[0] if largest_expenses else None
        top_category = category_rows[0]["category"] if category_rows else None
        top_category_share = round(category_rows[0]["share_percent"], 2) if category_rows else 0.0
        daily_totals = self._repository.daily_totals(report_month_key, "expense")
        monthly_trend = self._repository.monthly_spending("expense")[-6:]
        monthly_cash_flow_trend = self._repository.monthly_cash_flow()[-6:]

        insights = self._build_insights(
            report_month_label=now.strftime("%B %Y"),
            current_total=current_total,
            previous_total=previous_total,
            current_income_total=current_income_total,
            current_net_cash_flow=current_net_cash_flow,
            budget_variance=budget_variance,
            projected_month_end_spend=projected_month_end_spend,
            top_category=top_category,
            top_category_share=top_category_share,
            average_transaction=average_transaction,
            largest_transaction=largest_transaction,
        )
        recommendations = self._build_recommendations(
            remaining_budget=remaining_budget,
            projected_month_end_spend=projected_month_end_spend,
            monthly_budget=monthly_budget,
            net_cash_flow=current_net_cash_flow,
            largest_transaction=largest_transaction,
            top_category=top_category,
            top_category_share=top_category_share,
        )

        return ReportContext(
            report_month_key=report_month_key,
            previous_month_key=previous_month_key,
            report_month_label=now.strftime("%B %Y"),
            previous_month_label=previous_month_date.strftime("%B %Y"),
            monthly_budget=round(monthly_budget, 2),
            current_total=current_total,
            previous_total=previous_total,
            current_income_total=round(current_income_total, 2),
            previous_income_total=round(previous_income_total, 2),
            current_net_cash_flow=current_net_cash_flow,
            previous_net_cash_flow=previous_net_cash_flow,
            remaining_budget=remaining_budget,
            budget_variance=budget_variance,
            month_over_month_change=month_over_month_change,
            budget_utilization=budget_utilization,
            income_coverage_ratio=income_coverage_ratio,
            transaction_count=transaction_count,
            average_transaction=average_transaction,
            average_daily_spend=average_daily_spend,
            projected_month_end_spend=projected_month_end_spend,
            largest_transaction=largest_transaction,
            top_category=top_category,
            top_category_share=top_category_share,
            daily_totals=daily_totals,
            monthly_trend=monthly_trend,
            monthly_cash_flow_trend=monthly_cash_flow_trend,
            category_rows=category_rows,
            largest_expenses=largest_expenses,
            insights=insights,
            recommendations=recommendations,
        )

    def _build_story(self, context: ReportContext, chart_paths: list[Path | None]) -> list:
        styles = self._styles()
        story: list = [
            Paragraph("Budget Tracker Monthly Financial Report", styles["title"]),
            Spacer(1, 0.08 * inch),
            Paragraph(
                f"Reporting period: {context.report_month_label} | Generated on {datetime.now().strftime('%d %B %Y %H:%M')}",
                styles["subtitle"],
            ),
            Spacer(1, 0.22 * inch),
            Paragraph(
                (
                    f"This report summarises budget performance, spending momentum, category concentration, and"
                    f" transaction-level risk indicators for {context.report_month_label}. It is designed to support"
                    " month-end review and near-term spend control decisions."
                ),
                styles["body"],
            ),
            Spacer(1, 0.22 * inch),
            Paragraph("Executive KPI Snapshot", styles["section"]),
            Spacer(1, 0.08 * inch),
            Paragraph(
                "The snapshot below separates each KPI from its interpretation so values remain readable and the report explains what each number means.",
                styles["body"],
            ),
            Spacer(1, 0.08 * inch),
            self._build_kpi_table(context),
            Spacer(1, 0.18 * inch),
            Paragraph("Key insights", styles["section"]),
            self._build_bullets(context.insights, styles["body"]),
            Spacer(1, 0.18 * inch),
            Paragraph("Operational recommendations", styles["section"]),
            self._build_bullets(context.recommendations, styles["body"]),
            PageBreak(),
            Paragraph("Visual performance analysis", styles["section"]),
            Spacer(1, 0.1 * inch),
        ]

        chart_captions = [
            "Category spend comparison against the prior month",
            "Daily spend trajectory across the current month",
            "Six-month spending trend",
            "Cash inflow, outflow, and net cash-flow progression",
        ]
        for path, caption in zip(chart_paths, chart_captions):
            if path:
                story.append(Image(str(path), width=6.7 * inch, height=2.55 * inch))
                story.append(Paragraph(caption, styles["caption"]))
                story.append(Spacer(1, 0.18 * inch))

        story.extend(
            [
                Paragraph("Category variance analysis", styles["section"]),
                Spacer(1, 0.08 * inch),
                self._build_category_table(context),
                Spacer(1, 0.18 * inch),
                Paragraph("Cash-flow snapshot", styles["section"]),
                Spacer(1, 0.08 * inch),
                self._build_cash_flow_table(context),
                Spacer(1, 0.18 * inch),
                Paragraph("Largest transactions", styles["section"]),
                Spacer(1, 0.08 * inch),
                self._build_expense_table(context.largest_expenses),
            ]
        )
        return story

    def _build_category_rows(
        self,
        report_month_key: str,
        previous_month_key: str,
        current_total: float,
        report_expenses: list[Expense],
    ) -> list[dict]:
        current_data = dict(self._repository.category_totals(report_month_key))
        previous_data = dict(self._repository.category_totals(previous_month_key))
        counts: dict[str, int] = {}
        for expense in report_expenses:
            counts[expense.category] = counts.get(expense.category, 0) + 1

        rows = []
        for category in sorted(set(current_data) | set(previous_data)):
            current_amount = round(current_data.get(category, 0.0), 2)
            previous_amount = round(previous_data.get(category, 0.0), 2)
            rows.append(
                {
                    "category": category,
                    "current_amount": current_amount,
                    "previous_amount": previous_amount,
                    "variance": round(current_amount - previous_amount, 2),
                    "share_percent": round((current_amount / current_total) * 100, 2) if current_total else 0.0,
                    "transaction_count": counts.get(category, 0),
                }
            )
        rows.sort(key=lambda item: (-item["current_amount"], item["category"]))
        return rows

    def _build_insights(
        self,
        report_month_label: str,
        current_total: float,
        previous_total: float,
        current_income_total: float,
        current_net_cash_flow: float,
        budget_variance: float,
        projected_month_end_spend: float,
        top_category: str | None,
        top_category_share: float,
        average_transaction: float,
        largest_transaction: Expense | None,
    ) -> list[str]:
        insights = [
            f"{report_month_label} spend closed at GBP {current_total:.2f}, versus GBP {previous_total:.2f} in the previous month.",
            f"Recorded income for the period is GBP {current_income_total:.2f}, producing net cash flow of GBP {current_net_cash_flow:.2f}.",
            (
                f"Budget variance is GBP {abs(budget_variance):.2f} "
                + ("over plan." if budget_variance > 0 else "under plan.")
            ),
            f"Projected month-end run rate is GBP {projected_month_end_spend:.2f} based on current daily pace.",
            f"Average transaction value is GBP {average_transaction:.2f}.",
        ]
        if top_category:
            insights.append(
                f"{top_category} is the dominant category, accounting for {top_category_share:.1f}% of current-month spending."
            )
        if largest_transaction:
            insights.append(
                f"The largest single transaction was {largest_transaction.description} at GBP {largest_transaction.amount:.2f} on {largest_transaction.date}."
            )
        return insights

    def _build_recommendations(
        self,
        remaining_budget: float,
        projected_month_end_spend: float,
        monthly_budget: float,
        net_cash_flow: float,
        largest_transaction: Expense | None,
        top_category: str | None,
        top_category_share: float,
    ) -> list[str]:
        recommendations = []
        if projected_month_end_spend > monthly_budget:
            recommendations.append(
                "Introduce a short-term spending hold on discretionary categories until projected month-end spend falls below budget."
            )
        else:
            recommendations.append(
                "Maintain the current spending cadence while reviewing large ad hoc purchases before approval."
            )

        if net_cash_flow < 0:
            recommendations.append(
                "Prioritise incoming cash commitments and defer non-essential spend until net cash flow returns positive."
            )

        if top_category and top_category_share >= 40:
            recommendations.append(
                f"Review the {top_category} category in detail because concentration above 40% materially increases budget risk."
            )

        if largest_transaction:
            recommendations.append(
                f"Validate whether {largest_transaction.description} should be budgeted as a recurring cost or treated as a one-off exception."
            )

        recommendations.append(
            f"Remaining available budget is GBP {remaining_budget:.2f}; use this as the control threshold for the rest of the cycle."
        )
        return recommendations

    def _build_kpi_table(self, context: ReportContext) -> Table:
        styles = self._styles()
        rows = [
            [
                self._table_cell("KPI", styles["table_header"]),
                self._table_cell("Value", styles["table_header"]),
                self._table_cell("What it means", styles["table_header"]),
            ],
            [
                self._table_cell("Monthly budget", styles["table_label"]),
                self._table_cell(f"GBP {context.monthly_budget:.2f}", styles["table_value"]),
                self._table_cell("Your planned spending limit for the current reporting month.", styles["table_body"]),
            ],
            [
                self._table_cell("Current spend", styles["table_label"]),
                self._table_cell(f"GBP {context.current_total:.2f}", styles["table_value"]),
                self._table_cell("Actual expense transactions recorded so far in the current month.", styles["table_body"]),
            ],
            [
                self._table_cell("Cash in", styles["table_label"]),
                self._table_cell(f"GBP {context.current_income_total:.2f}", styles["table_value"]),
                self._table_cell("Income recorded for this month from income transactions and monthly income settings.", styles["table_body"]),
            ],
            [
                self._table_cell("Net cash flow", styles["table_label"]),
                self._table_cell(f"GBP {context.current_net_cash_flow:.2f}", styles["table_value"]),
                self._table_cell("Income minus expenses. Positive cash flow means more came in than went out.", styles["table_body"]),
            ],
            [
                self._table_cell("Remaining budget", styles["table_label"]),
                self._table_cell(f"GBP {context.remaining_budget:.2f}", styles["table_value"]),
                self._table_cell("Monthly budget minus current spend. This is the spend control amount for the rest of the month.", styles["table_body"]),
            ],
            [
                self._table_cell("Budget utilisation", styles["table_label"]),
                self._table_cell(f"{context.budget_utilization:.1f}%", styles["table_value"]),
                self._table_cell("Current spend as a percentage of the monthly budget.", styles["table_body"]),
            ],
            [
                self._table_cell("Income coverage", styles["table_label"]),
                self._table_cell(f"{context.income_coverage_ratio:.1f}%", styles["table_value"]),
                self._table_cell("Income divided by current spend. Very high values usually mean spending is still low compared with income.", styles["table_body"]),
            ],
            [
                self._table_cell("Projected month-end", styles["table_label"]),
                self._table_cell(f"GBP {context.projected_month_end_spend:.2f}", styles["table_value"]),
                self._table_cell("Estimated month-end spend if the current daily spending pace continues.", styles["table_body"]),
            ],
            [
                self._table_cell("MoM change", styles["table_label"]),
                self._table_cell(f"GBP {context.month_over_month_change:.2f}", styles["table_value"]),
                self._table_cell("Current month spend minus previous month spend. Negative means spending has reduced.", styles["table_body"]),
            ],
            [
                self._table_cell("Average transaction", styles["table_label"]),
                self._table_cell(f"GBP {context.average_transaction:.2f}", styles["table_value"]),
                self._table_cell("Average value of current-month expense transactions.", styles["table_body"]),
            ],
            [
                self._table_cell("Transactions", styles["table_label"]),
                self._table_cell(str(context.transaction_count), styles["table_value"]),
                self._table_cell("Number of expense transactions included in this monthly report.", styles["table_body"]),
            ],
            [
                self._table_cell("Previous net cash flow", styles["table_label"]),
                self._table_cell(f"GBP {context.previous_net_cash_flow:.2f}", styles["table_value"]),
                self._table_cell("Previous month income minus previous month expenses, used as the comparison baseline.", styles["table_body"]),
            ],
        ]
        table = Table(rows, repeatRows=1, colWidths=[1.65 * inch, 1.35 * inch, 3.55 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10203d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#e8f1ef")),
                    ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9d6df")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _build_cash_flow_table(self, context: ReportContext) -> Table:
        styles = self._styles()
        rows = [
            [
                self._table_cell("Metric", styles["table_header"]),
                self._table_cell(context.previous_month_label, styles["table_header"]),
                self._table_cell(context.report_month_label, styles["table_header"]),
                self._table_cell("Variance", styles["table_header"]),
            ],
            [
                self._table_cell("Income", styles["table_label"]),
                self._table_cell(f"GBP {context.previous_income_total:.2f}", styles["table_value"]),
                self._table_cell(f"GBP {context.current_income_total:.2f}", styles["table_value"]),
                self._table_cell(f"GBP {context.current_income_total - context.previous_income_total:.2f}", styles["table_value"]),
            ],
            [
                self._table_cell("Expenses", styles["table_label"]),
                self._table_cell(f"GBP {context.previous_total:.2f}", styles["table_value"]),
                self._table_cell(f"GBP {context.current_total:.2f}", styles["table_value"]),
                self._table_cell(f"GBP {context.current_total - context.previous_total:.2f}", styles["table_value"]),
            ],
            [
                self._table_cell("Net cash flow", styles["table_label"]),
                self._table_cell(f"GBP {context.previous_net_cash_flow:.2f}", styles["table_value"]),
                self._table_cell(f"GBP {context.current_net_cash_flow:.2f}", styles["table_value"]),
                self._table_cell(f"GBP {context.current_net_cash_flow - context.previous_net_cash_flow:.2f}", styles["table_value"]),
            ],
        ]
        table = Table(rows, repeatRows=1, colWidths=[1.6 * inch, 1.35 * inch, 1.35 * inch, 1.2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102a43")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d2d8de")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f7fafc")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _build_category_table(self, context: ReportContext) -> Table:
        styles = self._styles()
        rows = [[
            self._table_cell("Category", styles["table_header"]),
            self._table_cell("Current", styles["table_header"]),
            self._table_cell("Previous", styles["table_header"]),
            self._table_cell("Variance", styles["table_header"]),
            self._table_cell("Share", styles["table_header"]),
            self._table_cell("Transactions", styles["table_header"]),
        ]]
        rows.extend(
            [
                [
                    self._table_cell(row["category"], styles["table_label"]),
                    self._table_cell(f"GBP {row['current_amount']:.2f}", styles["table_value"]),
                    self._table_cell(f"GBP {row['previous_amount']:.2f}", styles["table_value"]),
                    self._table_cell(f"GBP {row['variance']:.2f}", styles["table_value"]),
                    self._table_cell(f"{row['share_percent']:.1f}%", styles["table_value"]),
                    self._table_cell(str(row["transaction_count"]), styles["table_value"]),
                ]
                for row in context.category_rows[:8]
            ]
        )

        table = Table(rows, repeatRows=1, colWidths=[1.55 * inch, 1.05 * inch, 1.05 * inch, 1.0 * inch, 0.8 * inch, 0.9 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#11413d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d2d8de")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f7fafc")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _build_expense_table(self, expenses: list[Expense]) -> Table:
        styles = self._styles()
        rows = [[
            self._table_cell("Date", styles["table_header"]),
            self._table_cell("Category", styles["table_header"]),
            self._table_cell("Description", styles["table_header"]),
            self._table_cell("Amount", styles["table_header"]),
        ]]
        rows.extend(
            [
                [
                    self._table_cell(expense.date, styles["table_body"]),
                    self._table_cell(expense.category, styles["table_label"]),
                    self._table_cell(expense.description, styles["table_body"]),
                    self._table_cell(f"GBP {expense.amount:.2f}", styles["table_value"]),
                ]
                for expense in expenses
            ]
            if expenses
            else [[
                self._table_cell("-", styles["table_body"]),
                self._table_cell("-", styles["table_body"]),
                self._table_cell("No transactions available for the current month.", styles["table_body"]),
                self._table_cell("GBP 0.00", styles["table_value"]),
            ]]
        )
        table = Table(rows, repeatRows=1, colWidths=[1.0 * inch, 1.15 * inch, 3.4 * inch, 0.95 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f5f59")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d2d8de")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fbf7f2"), colors.white]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _build_bullets(self, items: list[str], style: ParagraphStyle) -> ListFlowable:
        return ListFlowable(
            [ListItem(Paragraph(item, style)) for item in items],
            bulletType="bullet",
            leftIndent=14,
        )

    def _create_category_comparison_chart(self, context: ReportContext) -> Path | None:
        if not context.category_rows:
            return None

        rows = context.category_rows[:6]
        labels = [row["category"] for row in rows]
        current_values = [row["current_amount"] for row in rows]
        previous_values = [row["previous_amount"] for row in rows]

        figure, axis = plt.subplots(figsize=(8, 3))
        y_positions = range(len(labels))
        axis.barh(y_positions, previous_values, color="#c9d6df", label=context.previous_month_label)
        axis.barh(y_positions, current_values, color="#0f766e", alpha=0.9, label=context.report_month_label)
        axis.set_yticks(list(y_positions))
        axis.set_yticklabels(labels)
        axis.invert_yaxis()
        axis.set_xlabel("GBP")
        axis.set_title("Category spend comparison")
        axis.legend(frameon=False, loc="lower right")
        axis.spines[["top", "right"]].set_visible(False)
        return self._save_figure(figure)

    def _create_daily_spending_chart(self, context: ReportContext) -> Path | None:
        if not context.daily_totals:
            return None

        labels = [day[-2:] for day, _ in context.daily_totals]
        values = [value for _, value in context.daily_totals]

        figure, axis = plt.subplots(figsize=(8, 3))
        axis.plot(labels, values, color="#b45309", linewidth=2.3, marker="o", markersize=4)
        axis.fill_between(labels, values, color="#f5c892", alpha=0.35)
        axis.set_title("Daily spending pattern")
        axis.set_ylabel("GBP")
        axis.grid(axis="y", alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
        return self._save_figure(figure)

    def _create_monthly_trend_chart(self, context: ReportContext) -> Path | None:
        if not context.monthly_trend:
            return None

        labels = [datetime.strptime(month, "%Y-%m").strftime("%b %y") for month, _ in context.monthly_trend]
        values = [value for _, value in context.monthly_trend]

        figure, axis = plt.subplots(figsize=(8, 3))
        axis.plot(labels, values, color="#11413d", linewidth=2.5)
        axis.scatter(labels, values, color="#14b8a6", s=35, zorder=3)
        axis.set_title("Six-month spending trend")
        axis.set_ylabel("GBP")
        axis.grid(axis="y", alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
        return self._save_figure(figure)

    def _create_cash_flow_chart(self, context: ReportContext) -> Path | None:
        if not context.monthly_cash_flow_trend:
            return None

        labels = [
            datetime.strptime(item["month"], "%Y-%m").strftime("%b %y")
            for item in context.monthly_cash_flow_trend
        ]
        income_values = [item["income"] for item in context.monthly_cash_flow_trend]
        expense_values = [item["expense"] for item in context.monthly_cash_flow_trend]
        net_values = [item["net"] for item in context.monthly_cash_flow_trend]

        figure, axis = plt.subplots(figsize=(8, 3))
        axis.plot(labels, income_values, color="#0f766e", linewidth=2.2, marker="o", label="Cash in")
        axis.plot(labels, expense_values, color="#b45309", linewidth=2.2, marker="o", label="Cash out")
        axis.plot(labels, net_values, color="#1d4ed8", linewidth=2.2, marker="o", label="Net")
        axis.set_title("Cash-flow trend")
        axis.set_ylabel("GBP")
        axis.grid(axis="y", alpha=0.2)
        axis.legend(frameon=False, loc="upper left")
        axis.spines[["top", "right"]].set_visible(False)
        return self._save_figure(figure)

    def _save_figure(self, figure) -> Path:
        file_descriptor, raw_path = tempfile.mkstemp(prefix="budget-report-", suffix=".png")
        os.close(file_descriptor)
        path = Path(raw_path)
        figure.tight_layout()
        figure.savefig(path, dpi=180, bbox_inches="tight")
        plt.close(figure)
        return path

    def _styles(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "ReportTitle",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#102a43"),
                alignment=TA_CENTER,
            ),
            "subtitle": ParagraphStyle(
                "ReportSubtitle",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#52606d"),
                alignment=TA_CENTER,
            ),
            "section": ParagraphStyle(
                "ReportSection",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#11413d"),
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "ReportBody",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#243b53"),
            ),
            "caption": ParagraphStyle(
                "ReportCaption",
                parent=base["BodyText"],
                fontName="Helvetica-Oblique",
                fontSize=9,
                leading=11,
                textColor=colors.HexColor("#52606d"),
                alignment=TA_CENTER,
            ),
            "table_header": ParagraphStyle(
                "ReportTableHeader",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=10.5,
                textColor=colors.white,
            ),
            "table_label": ParagraphStyle(
                "ReportTableLabel",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=10.5,
                textColor=colors.HexColor("#10203d"),
                wordWrap="CJK",
            ),
            "table_value": ParagraphStyle(
                "ReportTableValue",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=10.5,
                textColor=colors.HexColor("#0f4f49"),
                wordWrap="CJK",
            ),
            "table_body": ParagraphStyle(
                "ReportTableBody",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=8,
                leading=10.5,
                textColor=colors.HexColor("#243b53"),
                wordWrap="CJK",
            ),
        }

    @staticmethod
    def _table_cell(value: object, style: ParagraphStyle) -> Paragraph:
        text = str(value if value is not None else "")
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )
        return Paragraph(escaped, style)

    def _decorate_page(self, canvas, document) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#102a43"))
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(document.leftMargin, letter[1] - 26, "Budget Tracker")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#52606d"))
        canvas.drawRightString(letter[0] - document.rightMargin, 22, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

