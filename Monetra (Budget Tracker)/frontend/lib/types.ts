export interface AuthSessionResponse {
  authenticated: boolean;
  username: string | null;
}

export interface Expense {
  id: number;
  date: string;
  category: string;
  description: string;
  amount: number;
  entry_type: "expense" | "income";
}

export interface ExpensePayload {
  date: string;
  category: string;
  description: string;
  amount: number | string;
  entry_type?: "expense" | "income";
}

export interface DashboardSummary {
  monthly_budget: number;
  current_month_total: number;
  monthly_expenses: number;
  monthly_income: number;
  income_month?: string;
  month_key?: string;
  net_cash_flow: number;
  remaining_budget: number;
  weekly_spending: number;
  percent_spent: number;
  status: "within" | "warning" | "over";
  month_label: string;
}

export interface CategoryInsight {
  category: string;
  amount: number;
}

export interface CategoryInsightsResponse {
  top_categories: CategoryInsight[];
  bottom_categories: CategoryInsight[];
  total_spending: number;
}

export interface WordCloudItem {
  label: string;
  value: number;
  share?: number;
}

export interface WordCloudResponse {
  top_category: string | null;
  top_category_total?: number;
  dominant_label?: string | null;
  dominant_value?: number;
  frequencies: WordCloudItem[];
}

export interface FinancialPulseResponse {
  health_score: number;
  average_transaction: number;
  transaction_count: number;
  spend_velocity: number;
  top_category_share: number;
  runway_days: number | null;
  narrative: string;
  cash_in: number;
  cash_out: number;
  net_cash_flow: number;
  income_coverage: number;
  recent_transactions: Expense[];
  recent_expenses: Expense[];
}

export interface PredictionResponse {
  next_month: string;
  predicted_spending: number;
  is_budget_exceeded: boolean;
  monthly_budget: number;
}

export interface ImportResponse {
  imported_rows: number;
  skipped_rows: number;
}

export interface FormState {
  date: string;
  category: string;
  description: string;
  amount: string;
  entry_type: "expense" | "income";
}

export interface SettingsResponse {
  monthly_budget: number;
  monthly_income: number;
  income_month?: string;
}

export interface RecurringItem {
  id: number;
  category: string;
  description: string;
  amount: number;
  entry_type: "expense" | "income";
  frequency: "weekly" | "monthly";
  start_date: string;
  end_date?: string | null;
  active: boolean;
}

export interface RecurringCalendarOccurrence {
  recurring_item_id: number;
  date: string;
  category: string;
  description: string;
  amount: number;
  entry_type: "expense" | "income";
  frequency: "weekly" | "monthly";
  days_until_due: number;
  updated_at?: string;
  is_paid?: boolean;
  transaction_id?: number | null;
}

export interface RecurringCalendarResponse {
  window_start: string;
  window_end: string;
  occurrences: RecurringCalendarOccurrence[];
  completed_occurrences: RecurringCalendarOccurrence[];
}

export interface RecurringItemPayload {
  category: string;
  description: string;
  amount: number | string;
  entry_type: "expense" | "income";
  frequency: "weekly" | "monthly";
  start_date: string;
  end_date?: string | null;
  active: boolean;
}

export interface AgentBriefingJob {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | string;
  task: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  result: AgentBriefingResponse | null;
}

export interface AgentTraceStep {
  tool: string;
  reason: string;
  arguments: Record<string, unknown>;
  result: unknown;
}

export interface AgentBriefingResponse {
  headline: string;
  summary: string;
  risk_level: "low" | "medium" | "high" | string;
  recommended_actions: string[];
  email_subject: string;
  email_draft: string;
  task: string;
  model: string;
  tools_used: string[];
  report_download_url: string | null;
  generated_at: string;
  action_result?: {
    type: string;
    message: string;
    recurring_item?: RecurringItem;
    payload?: Record<string, unknown>;
  };
  trace?: {
    memory: Array<Record<string, unknown>>;
    plan: {
      intent?: string;
      steps?: Array<{
        tool?: string;
        reason?: string;
        arguments?: Record<string, unknown>;
      }>;
      success_criteria?: string[];
    };
    execution_results: AgentTraceStep[];
    verification: {
      headline?: string;
      summary?: string;
      risk_level?: string;
      recommended_actions?: string[];
      email_subject?: string;
      email_draft?: string;
    };
    repair_attempts: number;
  };
}

export interface AgentWorkflowJob {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | string;
  workflow_name: string;
  task: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  result: AgentWorkflowRun | null;
}

export interface AgentWorkflowDefinition {
  id: string;
  label: string;
  description: string;
  automation_focus: string;
  default_task: string;
}

export interface AgentWorkflowRun {
  id: number;
  workflow_name: string;
  workflow_label: string;
  status: string;
  headline: string;
  summary: string;
  risk_level: "low" | "medium" | "high" | string;
  recommended_actions: string[];
  automated_actions: string[];
  email_subject: string;
  email_draft: string;
  task: string;
  model: string;
  tools_used: string[];
  report_download_url: string | null;
  generated_at: string;
}



