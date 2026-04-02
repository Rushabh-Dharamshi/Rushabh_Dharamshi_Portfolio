Feature: Recurring planner
  Recurring bills and purchases should stay visible and editable.

  Scenario: View recurring reminders from sample rows
    Given the budget tracker API is mocked with sample recurring rows
      | id | category | description    | amount | entry_type | frequency | start_date | active |
      | 1  | Housing  | Rent           | 700.00 | expense    | monthly   | 2026-03-01 | true   |
      | 2  | Travel   | Weekly commute | 45.00  | expense    | weekly    | 2026-03-24 | true   |
    When I open the budget tracker homepage
    Then I should see the text "Upcoming bills and frequent purchases"
    And I should see the text "Weekly commute"

  Scenario: Add a recurring reminder
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I click the button "Add reminder"
    Then I should see the text "Recurring item #3 created successfully."
    And I should see the text "Gym"

  Scenario: Update a recurring reminder
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I click the text "Rent"
    And I fill the field "Description" with "Updated rent"
    And I click the button "Update reminder"
    Then I should see the text "Recurring item #1 updated successfully."
    And I should see the text "Updated rent"
