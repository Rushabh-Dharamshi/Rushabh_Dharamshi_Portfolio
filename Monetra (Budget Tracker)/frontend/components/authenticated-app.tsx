"use client";

import { FormEvent, useEffect, useState } from "react";

import { BudgetTrackerShell } from "@/components/budget-tracker-shell";
import { apiClient, rememberExpectedUserId } from "@/lib/api-client";
import { formatBackendTimestamp } from "@/lib/date-time";
import { AuthSessionResponse, MockEmailMessage } from "@/lib/types";

const emptySession: AuthSessionResponse = {
  authenticated: false,
  user_id: null,
  username: null,
  email: null,
  registered_user_count: 0,
};

type AuthMode = "login" | "register" | "forgot";

function isLikelyMockEmail(value: string) {
  return /@(monetra\.test|example\.test)$/i.test(value.trim());
}

export function resolveMockInboxRecipient(recipientOverride: string | undefined, mockInboxEmailDraft: string): string {
  return String(recipientOverride ?? mockInboxEmailDraft).trim();
}

export function AuthenticatedApp() {
  const [session, setSession] = useState<AuthSessionResponse>(emptySession);
  const [mode, setMode] = useState<AuthMode>("login");
  const [usernameDraft, setUsernameDraft] = useState("Rushabh");
  const [emailDraft, setEmailDraft] = useState("");
  const [passwordDraft, setPasswordDraft] = useState("");
  const [confirmPasswordDraft, setConfirmPasswordDraft] = useState("");
  const [resetIdentifierDraft, setResetIdentifierDraft] = useState("");
  const [resetTokenDraft, setResetTokenDraft] = useState("");
  const [resetPasswordDraft, setResetPasswordDraft] = useState("");
  const [mockInboxEmailDraft, setMockInboxEmailDraft] = useState("");
  const [mockInboxMessages, setMockInboxMessages] = useState<MockEmailMessage[]>([]);
  const [isInboxLoading, setIsInboxLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const currentSession = await apiClient.getAuthSession();
        rememberExpectedUserId(currentSession.user_id);
        setSession(currentSession);
      } catch {
        rememberExpectedUserId(null);
        setSession(emptySession);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setErrorMessage(null);
      setStatusMessage(null);
      setIsSubmitting(true);
      const nextSession = await apiClient.login(usernameDraft, passwordDraft);
      rememberExpectedUserId(nextSession.user_id);
      setSession(nextSession);
      setPasswordDraft("");
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (passwordDraft !== confirmPasswordDraft) {
      setErrorMessage("Passwords do not match.");
      return;
    }
    if (
      passwordDraft.trim().toLowerCase() === usernameDraft.trim().toLowerCase()
      || passwordDraft.trim().toLowerCase() === emailDraft.trim().toLowerCase()
    ) {
      setErrorMessage("Password must be different from the username and email.");
      return;
    }
    try {
      setErrorMessage(null);
      setStatusMessage(null);
      setIsSubmitting(true);
      const nextSession = await apiClient.register(usernameDraft, emailDraft, passwordDraft);
      rememberExpectedUserId(nextSession.user_id);
      setSession(nextSession);
      setPasswordDraft("");
      setConfirmPasswordDraft("");
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleForgotPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setErrorMessage(null);
      setStatusMessage(null);
      setIsSubmitting(true);
      const result = await apiClient.requestPasswordReset(resetIdentifierDraft);
      setStatusMessage(result.reset_token ? `${result.message} Reset code: ${result.reset_token}` : result.message);
      if (result.reset_token) {
        setResetTokenDraft(result.reset_token);
      }
      if (isLikelyMockEmail(resetIdentifierDraft)) {
        const recipient = resetIdentifierDraft.trim();
        setMockInboxEmailDraft(recipient);
        await refreshMockInbox(recipient, false);
      }
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function refreshMockInbox(recipientOverride?: string, showEmptyStatus = true) {
    const recipient = resolveMockInboxRecipient(recipientOverride, mockInboxEmailDraft);
    if (!recipient) {
      setErrorMessage("Enter a demo email address such as user001@monetra.test.");
      return;
    }
    try {
      setErrorMessage(null);
      setIsInboxLoading(true);
      const inbox = await apiClient.getMockEmailInbox(recipient);
      setMockInboxEmailDraft(inbox.recipient);
      setMockInboxMessages(inbox.messages);
      if (showEmptyStatus && inbox.messages.length === 0) {
        setStatusMessage("No simulated emails found for that demo inbox yet.");
      }
    } catch (error) {
      setMockInboxMessages([]);
      setErrorMessage((error as Error).message);
    } finally {
      setIsInboxLoading(false);
    }
  }

  async function handleResetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setErrorMessage(null);
      setStatusMessage(null);
      setIsSubmitting(true);
      const result = await apiClient.resetPassword(resetTokenDraft, resetPasswordDraft);
      setStatusMessage(result.message);
      setResetTokenDraft("");
      setResetPasswordDraft("");
      setPasswordDraft("");
      setMode("login");
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    try {
      setErrorMessage(null);
      setStatusMessage(null);
      await apiClient.logout();
      const nextSession = await apiClient.getAuthSession();
      rememberExpectedUserId(nextSession.user_id);
      setSession(nextSession);
    } catch (error) {
      setErrorMessage((error as Error).message);
    }
  }

  async function handleDeleteAccount() {
    const confirmed = window.confirm(
      "Permanently delete this Monetra account and all linked finance data? This cannot be undone.",
    );
    if (!confirmed) {
      return;
    }
    try {
      setErrorMessage(null);
      setStatusMessage(null);
      const result = await apiClient.deleteCurrentUser();
      rememberExpectedUserId(null);
      setSession({
        ...emptySession,
        registered_user_count: result.registered_user_count,
      });
      setStatusMessage(result.message);
    } catch (error) {
      setErrorMessage((error as Error).message);
    }
  }

  function renderMockInboxPanel(options: { signedInDemo?: boolean } = {}) {
    const signedInDemo = Boolean(options.signedInDemo);
    const defaultEmail = signedInDemo && session.email ? session.email : mockInboxEmailDraft;
    return (
      <section className={signedInDemo ? "mock-inbox-panel signed-in-mock-inbox" : "mock-inbox-panel"} aria-label="Demo email inbox">
        <div className="mock-inbox-heading">
          <div>
            <p className="eyebrow">Demo email inbox</p>
            <h2>{signedInDemo ? "Simulated report emails" : "View simulated emails"}</h2>
          </div>
          <span>Mock only</span>
        </div>
        <p>
          {signedInDemo
            ? "This demo account uses simulated email delivery. Password reset messages and financial report emails appear here instead of going to Gmail."
            : <>Use this for demo accounts such as <strong>user001@monetra.test</strong>. Real Gmail inboxes never appear here.</>}
        </p>
        <div className="mock-inbox-controls">
          <label className="field-group">
            <span>Demo email address</span>
            <input
              type="email"
              value={defaultEmail}
              onChange={(event) => setMockInboxEmailDraft(event.target.value)}
              placeholder="user001@monetra.test"
              readOnly={signedInDemo}
            />
          </label>
          <button
            className="secondary-button reset-password-button"
            type="button"
            onClick={() => void refreshMockInbox(defaultEmail)}
            disabled={isInboxLoading}
          >
            {isInboxLoading ? "Refreshing..." : "Refresh demo inbox"}
          </button>
        </div>
        <div className="mock-inbox-list">
          {mockInboxMessages.length ? (
            mockInboxMessages.map((message) => (
              <article className="mock-email-card" key={message.id}>
                <div className="mock-email-meta">
                  <strong>{message.subject}</strong>
                  <span>{formatBackendTimestamp(message.created_at)}</span>
                </div>
                <div className="mock-email-addresses">
                  <span>From {message.sender}</span>
                  <span>To {message.recipient}</span>
                </div>
                <pre>{message.body}</pre>
                {message.attachment_name ? (
                  message.attachment_url ? (
                    <a className="mock-email-attachment" href={message.attachment_url} download>
                      Download PDF attachment: {message.attachment_name}
                    </a>
                  ) : (
                    <span className="mock-email-attachment">Attachment: {message.attachment_name}</span>
                  )
                ) : null}
              </article>
            ))
          ) : (
            <p className="muted">Simulated reset codes and report emails for demo users will appear here.</p>
          )}
        </div>
      </section>
    );
  }

  if (isLoading) {
    return <main className="page-shell"><div className="panel">Checking login session...</div></main>;
  }

  if (!session.authenticated) {
    return (
      <main className="login-shell">
        <section className="login-card">
          <p className="eyebrow">Monetra</p>
          <h1>
            {mode === "register"
              ? "Create your private finance workspace."
              : mode === "forgot"
                ? "Recover access to your finance workspace."
                : "Sign in to your private finance workspace."}
          </h1>
          <p className="hero-copy">
            Each account has its own dashboard, records, recurring reminders, reports, and automation history.
          </p>
          <p className="auth-debug-count">
            Registered users in this system: {session.registered_user_count ?? 0}
          </p>

          <div className="auth-mode-tabs" role="tablist" aria-label="Authentication options">
            <button className={mode === "login" ? "auth-tab is-active" : "auth-tab"} type="button" onClick={() => setMode("login")}>
              Login
            </button>
            <button className={mode === "register" ? "auth-tab is-active" : "auth-tab"} type="button" onClick={() => setMode("register")}>
              Register
            </button>
            <button className={mode === "forgot" ? "auth-tab is-active" : "auth-tab"} type="button" onClick={() => setMode("forgot")}>
              Forgot password
            </button>
          </div>

          {mode === "login" ? (
            <form className="login-form" onSubmit={handleLogin}>
              <label className="field-group">
                <span>Username or email</span>
                <input
                  value={usernameDraft}
                  onChange={(event) => setUsernameDraft(event.target.value)}
                  autoComplete="username"
                  required
                />
              </label>

              <label className="field-group">
                <span>Password</span>
                <input
                  type="password"
                  value={passwordDraft}
                  onChange={(event) => setPasswordDraft(event.target.value)}
                  autoComplete="current-password"
                  required
                />
              </label>

              {errorMessage ? <div className="message error">{errorMessage}</div> : null}
              {statusMessage ? <div className="message success">{statusMessage}</div> : null}

              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Signing in..." : "Login"}
              </button>
            </form>
          ) : null}

          {mode === "register" ? (
            <form className="login-form" onSubmit={handleRegister}>
              <label className="field-group">
                <span>Username</span>
                <input
                  value={usernameDraft}
                  onChange={(event) => setUsernameDraft(event.target.value)}
                  autoComplete="username"
                  required
                />
              </label>
              <label className="field-group">
                <span>Email</span>
                <input
                  type="email"
                  value={emailDraft}
                  onChange={(event) => setEmailDraft(event.target.value)}
                  autoComplete="email"
                  required
                />
              </label>
              <label className="field-group">
                <span>Password</span>
                <input
                  type="password"
                  value={passwordDraft}
                  onChange={(event) => setPasswordDraft(event.target.value)}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label className="field-group">
                <span>Confirm password</span>
                <input
                  type="password"
                  value={confirmPasswordDraft}
                  onChange={(event) => setConfirmPasswordDraft(event.target.value)}
                  autoComplete="new-password"
                  required
                />
              </label>

              {errorMessage ? <div className="message error">{errorMessage}</div> : null}

              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating account..." : "Register"}
              </button>
            </form>
          ) : null}

          {mode === "forgot" ? (
            <div className="login-form">
              <form className="login-form compact-auth-form" onSubmit={handleForgotPassword}>
                <label className="field-group">
                  <span>Username or email</span>
                  <input
                    value={resetIdentifierDraft}
                    onChange={(event) => setResetIdentifierDraft(event.target.value)}
                    autoComplete="username"
                    required
                  />
                </label>
                <button className="primary-button" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Sending code..." : "Send reset code"}
                </button>
              </form>

              <form className="login-form compact-auth-form" onSubmit={handleResetPassword}>
                <label className="field-group">
                  <span>Reset code</span>
                  <input
                    value={resetTokenDraft}
                    onChange={(event) => setResetTokenDraft(event.target.value)}
                    autoComplete="one-time-code"
                    required
                  />
                </label>
                <label className="field-group">
                  <span>New password</span>
                  <input
                    type="password"
                    value={resetPasswordDraft}
                    onChange={(event) => setResetPasswordDraft(event.target.value)}
                    autoComplete="new-password"
                    required
                  />
                </label>
                <button className="secondary-button reset-password-button" type="submit" disabled={isSubmitting}>
                  Reset password
                </button>
              </form>

              {renderMockInboxPanel()}

              {errorMessage ? <div className="message error">{errorMessage}</div> : null}
              {statusMessage ? <div className="message success">{statusMessage}</div> : null}
            </div>
          ) : null}
        </section>
      </main>
    );
  }

  return (
    <BudgetTrackerShell
      username={session.username ?? "Rushabh"}
      onLogout={handleLogout}
      onDeleteAccount={handleDeleteAccount}
      demoEmailInbox={isLikelyMockEmail(session.email ?? "") ? renderMockInboxPanel({ signedInDemo: true }) : undefined}
    />
  );
}
