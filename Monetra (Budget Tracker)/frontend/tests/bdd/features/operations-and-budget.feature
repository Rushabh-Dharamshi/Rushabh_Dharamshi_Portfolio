Feature: Operations and budget controls
  Budget settings and forecasting should remain easy to validate through the frontend API contract.

  Scenario: Save monthly controls and predict next month spending
    Given the budget tracker API is mocked
    When I save the monthly budget "1200"
    Then the latest result should contain the text "1200"
    When I save the monthly income "1700" for month "2026-04"
    Then the latest result should contain the text "1700"
    When I request the next month prediction
    Then the latest result should contain the text "April 2026"
