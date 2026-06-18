import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ReactNode } from "react";

import { AuthenticatedApp } from "@/components/authenticated-app";
import { apiClient } from "@/lib/api-client";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    getAuthSession: jest.fn(),
    login: jest.fn(),
    register: jest.fn(),
    requestPasswordReset: jest.fn(),
    getMockEmailInbox: jest.fn(),
    resetPassword: jest.fn(),
    logout: jest.fn(),
    deleteCurrentUser: jest.fn(),
  },
}));

jest.mock("@/components/budget-tracker-shell", () => ({
  BudgetTrackerShell: ({
    username,
    onLogout,
    onDeleteAccount,
    demoEmailInbox,
  }: {
    username: string;
    onLogout?: () => void;
    onDeleteAccount?: () => void;
    demoEmailInbox?: ReactNode;
  }) => (
    <div>
      <span>Shell for {username}</span>
      {demoEmailInbox}
      <button type="button" onClick={() => onLogout?.()}>
        Trigger logout
      </button>
      <button type="button" onClick={() => onDeleteAccount?.()}>
        Trigger delete account
      </button>
    </div>
  ),
}));

describe("AuthenticatedApp", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("renders the login form when no session exists and completes login", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null, registered_user_count: 3 });
    (apiClient.login as jest.Mock).mockResolvedValue({ authenticated: true, username: "Rushabh" });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Sign in to your private finance workspace.")).toBeInTheDocument();
    });
    expect(screen.getByText("Registered users in this system: 3")).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue("Rushabh"), { target: { value: "Owner" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Login" })[1]);

    await waitFor(() => {
      expect(screen.getByText("Shell for Rushabh")).toBeInTheDocument();
    });

    expect(apiClient.login).toHaveBeenCalledWith("Owner", "secret");
  });

  it("falls back to the login form when the session check fails and surfaces login errors", async () => {
    (apiClient.getAuthSession as jest.Mock).mockRejectedValue(new Error("offline"));
    (apiClient.login as jest.Mock).mockRejectedValue(new Error("Invalid credentials"));

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Sign in to your private finance workspace.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Login" })[1]);

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("allows logout and shows logout errors without dropping the shell", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: true, username: "Rushabh" });
    (apiClient.logout as jest.Mock)
      .mockRejectedValueOnce(new Error("Logout failed"))
      .mockResolvedValueOnce({ message: "ok" });
    (apiClient.getAuthSession as jest.Mock)
      .mockResolvedValueOnce({ authenticated: true, username: "Rushabh" })
      .mockResolvedValueOnce({ authenticated: false, username: null, registered_user_count: 4 });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Shell for Rushabh")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Trigger logout"));
    await waitFor(() => {
      expect(apiClient.logout).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText("Shell for Rushabh")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Trigger logout"));
    await waitFor(() => {
      expect(screen.getByText("Sign in to your private finance workspace.")).toBeInTheDocument();
    });
    expect(screen.getByText("Registered users in this system: 4")).toBeInTheDocument();
  });

  it("deletes the signed-in account after confirmation", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: true, username: "Rushabh_4" });
    (apiClient.deleteCurrentUser as jest.Mock).mockResolvedValue({
      message: "User account and all linked finance data were permanently deleted.",
      registered_user_count: 3,
    });
    jest.spyOn(window, "confirm").mockReturnValue(true);

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Shell for Rushabh_4")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Trigger delete account"));

    await waitFor(() => {
      expect(screen.getByText("Sign in to your private finance workspace.")).toBeInTheDocument();
    });
    expect(screen.getByText("Registered users in this system: 3")).toBeInTheDocument();
    expect(apiClient.deleteCurrentUser).toHaveBeenCalled();
  });

  it("registers a new user from the auth card", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null, registered_user_count: 3 });
    (apiClient.register as jest.Mock).mockResolvedValue({ authenticated: true, username: "NewUser", email: "new@example.com" });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Register")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Register"));
    fireEvent.click(screen.getAllByRole("button", { name: "Login" })[0]);
    fireEvent.click(screen.getByText("Register"));
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "NewUser" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "password123" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Register" })[1]);

    await waitFor(() => {
      expect(screen.getByText("Shell for NewUser")).toBeInTheDocument();
    });

    expect(apiClient.register).toHaveBeenCalledWith("NewUser", "new@example.com", "password123");
  });

  it("blocks registration when the password matches the username or email", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null, registered_user_count: 3 });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Register")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Register"));
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "NewUser" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "NewUser" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "NewUser" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Register" })[1]);

    expect(screen.getByText("Password must be different from the username and email.")).toBeInTheDocument();
    expect(apiClient.register).not.toHaveBeenCalled();
  });

  it("blocks mismatched registration passwords and surfaces register errors", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null, registered_user_count: 3 });
    (apiClient.register as jest.Mock).mockRejectedValue(new Error("Username already exists"));

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Register")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Register"));
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "NewUser" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "different123" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Register" })[1]);

    expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
    expect(apiClient.register).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "password123" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Register" })[1]);

    await waitFor(() => {
      expect(screen.getByText("Username already exists")).toBeInTheDocument();
    });
  });

  it("requests and applies a password reset code", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null });
    (apiClient.requestPasswordReset as jest.Mock).mockResolvedValue({ message: "Reset sent", reset_token: "abc123" });
    (apiClient.resetPassword as jest.Mock).mockResolvedValue({ message: "Password updated" });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Forgot password")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Forgot password"));
    fireEvent.change(screen.getByLabelText("Username or email"), { target: { value: "new@example.com" } });
    fireEvent.click(screen.getByText("Send reset code"));

    await waitFor(() => {
      expect(screen.getByText("Reset sent Reset code: abc123")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass123" } });
    fireEvent.click(screen.getByText("Reset password"));

    await waitFor(() => {
      expect(screen.getByText("Password updated")).toBeInTheDocument();
    });
    expect(apiClient.resetPassword).toHaveBeenCalledWith("abc123", "newpass123");
  });

  it("shows simulated reset emails in the demo inbox", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null });
    (apiClient.requestPasswordReset as jest.Mock).mockResolvedValue({ message: "Reset sent" });
    (apiClient.getMockEmailInbox as jest.Mock).mockResolvedValue({
      recipient: "user001@monetra.test",
      messages: [
        {
          id: 1,
          recipient: "user001@monetra.test",
          sender: "demo@monetra.test",
          subject: "Monetra password reset code",
          body: "Your Monetra password reset code is:\n\nabc123\n",
          status: "simulated",
          has_attachment: false,
          attachment_name: null,
          attachment_url: null,
          created_at: "2026-06-16T12:00:00Z",
        },
      ],
    });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Forgot password")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Forgot password"));
    fireEvent.change(screen.getByLabelText("Username or email"), { target: { value: "user001@monetra.test" } });
    fireEvent.click(screen.getByText("Send reset code"));

    await waitFor(() => {
      expect(screen.getByText("Monetra password reset code")).toBeInTheDocument();
    });
    expect(screen.getByText(/abc123/)).toBeInTheDocument();
    expect(apiClient.getMockEmailInbox).toHaveBeenCalledWith("user001@monetra.test");
  });

  it("handles forgot/reset errors and demo inbox empty/error states", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null });
    (apiClient.requestPasswordReset as jest.Mock).mockRejectedValueOnce(new Error("Reset unavailable"));
    (apiClient.resetPassword as jest.Mock).mockRejectedValueOnce(new Error("Invalid reset code"));
    (apiClient.getMockEmailInbox as jest.Mock)
      .mockResolvedValueOnce({ recipient: "user001@monetra.test", messages: [] })
      .mockRejectedValueOnce(new Error("Inbox unavailable"));

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Forgot password")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Forgot password"));
    fireEvent.change(screen.getByLabelText("Username or email"), { target: { value: "real@example.com" } });
    fireEvent.click(screen.getByText("Send reset code"));
    await waitFor(() => {
      expect(screen.getByText("Reset unavailable")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Reset code"), { target: { value: "bad-token" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass123" } });
    fireEvent.click(screen.getByText("Reset password"));
    await waitFor(() => {
      expect(screen.getByText("Invalid reset code")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Refresh demo inbox"));
    expect(screen.getByText("Enter a demo email address such as user001@monetra.test.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Demo email address"), { target: { value: "user001@monetra.test" } });
    fireEvent.click(screen.getByText("Refresh demo inbox"));
    await waitFor(() => {
      expect(screen.getByText("No simulated emails found for that demo inbox yet.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Refresh demo inbox"));
    await waitFor(() => {
      expect(screen.getByText("Inbox unavailable")).toBeInTheDocument();
    });
  });

  it("cancels and handles errors when deleting a signed-in account", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: true, username: "Rushabh_4" });
    (apiClient.deleteCurrentUser as jest.Mock).mockRejectedValue(new Error("Delete failed"));
    const confirmSpy = jest.spyOn(window, "confirm");
    confirmSpy.mockReturnValueOnce(false).mockReturnValueOnce(true);

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Shell for Rushabh_4")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Trigger delete account"));
    expect(apiClient.deleteCurrentUser).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("Trigger delete account"));
    await waitFor(() => {
      expect(apiClient.deleteCurrentUser).toHaveBeenCalledTimes(1);
    });
  });

  it("shows the demo inbox on the main screen for signed-in demo users with a clickable report attachment", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({
      authenticated: true,
      username: "DemoUser",
      email: "demo.user@monetra.test",
    });
    (apiClient.getMockEmailInbox as jest.Mock).mockResolvedValue({
      recipient: "demo.user@monetra.test",
      messages: [
        {
          id: 9,
          recipient: "demo.user@monetra.test",
          sender: "demo@monetra.test",
          subject: "Month-end finance report",
          body: "Your monthly report is attached.\n",
          status: "simulated",
          has_attachment: true,
          attachment_name: "monthly-report.pdf",
          attachment_url: "/api/reports/monthly",
          created_at: "2026-06-16T13:00:00Z",
        },
        {
          id: 10,
          recipient: "demo.user@monetra.test",
          sender: "demo@monetra.test",
          subject: "Report generated without link",
          body: "Attachment is stored in the mock inbox.",
          status: "simulated",
          has_attachment: true,
          attachment_name: "stored-report.pdf",
          attachment_url: null,
          created_at: "2026-06-16T13:01:00Z",
        },
      ],
    });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Shell for DemoUser")).toBeInTheDocument();
    });
    expect(screen.getByText("Simulated report emails")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Refresh demo inbox"));

    await waitFor(() => {
      expect(screen.getByText("Month-end finance report")).toBeInTheDocument();
    });
    const reportLink = screen.getByRole("link", { name: "Download PDF attachment: monthly-report.pdf" });
    expect(reportLink).toHaveAttribute("href", "/api/reports/monthly");
    expect(screen.getByText("Attachment: stored-report.pdf")).toBeInTheDocument();
    expect(apiClient.getMockEmailInbox).toHaveBeenCalledWith("demo.user@monetra.test");
  });
});
