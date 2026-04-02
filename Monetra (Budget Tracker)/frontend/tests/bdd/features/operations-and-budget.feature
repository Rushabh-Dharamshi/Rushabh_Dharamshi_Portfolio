Feature: Operations and budget controls
  Budget editing and reporting actions should remain easy to follow.

  Scenario: Predict next month spending
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I click the button "Predict next month"
    Then I should see the text "April 2026"

  Scenario: Save the monthly budget
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I fill the field "Monthly budget (GBP)" with "1200"
    And I click the button "Save budget"
    Then I should see the text "Monthly budget updated to GBP 1200.00."
    And I should see the value "1200.00"

  Scenario: Check budget status
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I click the button "Check budget status"
    Then I should see the text "spent GBP 420.00"
