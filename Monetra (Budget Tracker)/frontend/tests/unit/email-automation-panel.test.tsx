import { fireEvent, render, screen } from "@testing-library/react";

import { EmailAutomationPanel } from "@/components/email-automation-panel";

describe("EmailAutomationPanel", () => {
  it("renders empty state and forwards dispatch actions", () => {
    const onSendUpcomingBillsEmail = jest.fn();
    const onSendMonthEndEmail = jest.fn();

    render(
      <EmailAutomationPanel
        runs={[]}
        activeDispatchId={null}
        onSendUpcomingBillsEmail={onSendUpcomingBillsEmail}
        onSendMonthEndEmail={onSendMonthEndEmail}
      />,
    );

    expect(screen.getByText("Manual and scheduled email dispatches will appear here once they run.")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Send upcoming bills email"));
    fireEvent.click(screen.getByText("Send month-end report"));

    expect(onSendUpcomingBillsEmail).toHaveBeenCalled();
    expect(onSendMonthEndEmail).toHaveBeenCalled();
  });

  it("shows active dispatch state and filters to email runs only", () => {
    render(
      <EmailAutomationPanel
        runs={[
          {
            id: 1,
            workflow_name: "month_end_email",
            workflow_label: "Month-end email",
            status: "completed",
            headline: "Month-end sent",
            summary: "Month-end report delivered.",
            risk_level: "high",
            recommended_actions: [],
            automated_actions: [],
            email_subject: "March close",
            email_draft: "done",
            task: "send",
            model: "mistral",
            tools_used: [],
            report_download_url: "/report.pdf",
            generated_at: "invalid timestamp",
          },
          {
            id: 2,
            workflow_name: "upcoming_bills_email",
            workflow_label: "Upcoming bills email",
            status: "completed",
            headline: "Upcoming bills sent",
            summary: "Upcoming bills email delivered.",
            risk_level: "medium",
            recommended_actions: [],
            automated_actions: [],
            email_subject: "Due soon",
            email_draft: "done",
            task: "send",
            model: "qwen",
            tools_used: [],
            report_download_url: null,
            generated_at: "2026-04-03T12:00:00Z",
          },
          {
            id: 3,
            workflow_name: "month_end_close",
            workflow_label: "Month-end close",
            status: "completed",
            headline: "ignore",
            summary: "ignore",
            risk_level: "low",
            recommended_actions: [],
            automated_actions: [],
            email_subject: "ignore",
            email_draft: "ignore",
            task: "ignore",
            model: "ignore",
            tools_used: [],
            report_download_url: null,
            generated_at: "2026-04-03T12:00:00Z",
          },
        ]}
        activeDispatchId="upcoming_bills_email"
        onSendUpcomingBillsEmail={jest.fn()}
        onSendMonthEndEmail={jest.fn()}
      />,
    );

    expect(screen.getByText("Email automation is running.")).toBeInTheDocument();
    expect(screen.getByText("Sending upcoming bills email...")).toBeDisabled();
    expect(screen.getByText("Send month-end report")).toBeEnabled();
    expect(screen.getByText("2 logged")).toBeInTheDocument();
    expect(screen.getByText("Month-end email")).toBeInTheDocument();
    expect(screen.getByText("Upcoming bills email")).toBeInTheDocument();
    expect(screen.getByText("invalid timestamp")).toBeInTheDocument();
    expect(screen.getByText("high risk")).toBeInTheDocument();
    expect(screen.getByText("medium risk")).toBeInTheDocument();
    expect(screen.getByText("Download report")).toHaveAttribute("href", "/report.pdf");
    expect(screen.queryByText("Month-end close")).not.toBeInTheDocument();
  });
});
