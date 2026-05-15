Feature: Dashboard overview
  The finance dashboard contract should surface core KPI and analytics signals.

  Scenario: View the dashboard summary payload
    Given the budget tracker API is mocked
    When I request the dashboard summary
    Then the latest result should contain the text "March 2026"
    And the latest result should contain the text "within"

  Scenario: View the financial pulse and category word cloud
    Given the budget tracker API is mocked
    When I request the financial pulse
    Then the latest result should contain the text "Steady spending rhythm."
    When I request the category word cloud
    Then the latest result should contain the text "Groceries"
