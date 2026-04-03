import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { AuthenticatedApp } from "@/components/authenticated-app";
import { apiClient } from "@/lib/api-client";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    getAuthSession: jest.fn(),
    login: jest.fn(),
    logout: jest.fn(),
  },
}));

jest.mock("@/components/budget-tracker-shell", () => ({
  BudgetTrackerShell: ({ username, onLogout }: { username: string; onLogout?: () => void }) => (
    <div>
      <span>Shell for {username}</span>
      <button type="button" onClick={() => onLogout?.()}>
        Trigger logout
      </button>
    </div>
  ),
}));

describe("AuthenticatedApp", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("renders the login form when no session exists and completes login", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: false, username: null });
    (apiClient.login as jest.Mock).mockResolvedValue({ authenticated: true, username: "Rushabh" });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Sign in to your private finance workspace.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByDisplayValue("Rushabh"), { target: { value: "Owner" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByText("Sign in"));

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
    fireEvent.click(screen.getByText("Sign in"));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("allows logout and shows logout errors without dropping the shell", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: true, username: "Rushabh" });
    (apiClient.logout as jest.Mock)
      .mockRejectedValueOnce(new Error("Logout failed"))
      .mockResolvedValueOnce({ message: "ok" });

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
  });
});
