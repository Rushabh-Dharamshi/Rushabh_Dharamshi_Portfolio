Feature: Dashboard overview
  The finance dashboard should surface the primary KPIs and analytics first.

  Scenario: View the financial pulse section
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    Then I should see the text "Financial pulse"

  Scenario: View the dashboard month label
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    Then I should see the text "March 2026"

  Scenario: View the category word cloud content
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    Then I should see the text "Groceries"
