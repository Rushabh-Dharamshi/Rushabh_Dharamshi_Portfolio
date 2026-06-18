Feature: Finance API behavior
  Backend finance workflows should be testable in business language.

  Scenario: Registering a user and adding an expense updates the dashboard
    Given a fresh Monetra API
    When I register a user named "DemoUser" with email "demo.user@monetra.test"
    And I add an expense of 12.50 for "Portfolio lunch" in category "Food"
    Then the expense list should include "Portfolio lunch"
    And the dashboard monthly expenses should be at least 12.50

  Scenario: Demo password reset email appears in the mock inbox
    Given a fresh Monetra API
    When I register a user named "ResetDemo" with email "reset.user@monetra.test"
    And I request a password reset for "reset.user@monetra.test"
    Then the mock inbox for "reset.user@monetra.test" should contain "Monetra password reset code"

  Scenario: Latency report records API calls
    Given a fresh Monetra API
    When I register a user named "LatencyDemo" with email "latency.user@monetra.test"
    And I request the dashboard
    Then the latency report should include a "GET" call to "/api/dashboard"
