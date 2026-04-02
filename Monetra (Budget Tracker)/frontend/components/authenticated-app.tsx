"use client";

import { FormEvent, useEffect, useState } from "react";

import { BudgetTrackerShell } from "@/components/budget-tracker-shell";
import { apiClient } from "@/lib/api-client";
import { AuthSessionResponse } from "@/lib/types";

const emptySession: AuthSessionResponse = {
  authenticated: false,
  username: null,
};

export function AuthenticatedApp() {
  const [session, setSession] = useState<AuthSessionResponse>(emptySession);
  const [usernameDraft, setUsernameDraft] = useState("Rushabh");
  const [passwordDraft, setPasswordDraft] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const currentSession = await apiClient.getAuthSession();
        setSession(currentSession);
      } catch {
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
      setIsSubmitting(true);
      const nextSession = await apiClient.login(usernameDraft, passwordDraft);
      setSession(nextSession);
      setPasswordDraft("");
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    try {
      setErrorMessage(null);
      await apiClient.logout();
      setSession(emptySession);
    } catch (error) {
      setErrorMessage((error as Error).message);
    }
  }

  if (isLoading) {
    return <main className="page-shell"><div className="panel">Checking login session...</div></main>;
  }

  if (!session.authenticated) {
    return (
      <main className="login-shell">
        <section className="login-card">
          <p className="eyebrow">Monetra</p>
          <h1>Sign in to your private finance workspace.</h1>
          <p className="hero-copy">
            This deployment is configured for a single owner account. Sign in to access the dashboard,
            reports, and automation workflows.
          </p>

          <form className="login-form" onSubmit={handleLogin}>
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

            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return <BudgetTrackerShell username={session.username ?? "Rushabh"} onLogout={handleLogout} />;
}
