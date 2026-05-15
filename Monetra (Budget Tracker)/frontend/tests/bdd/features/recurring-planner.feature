Feature: Recurring planner
  Recurring bills and purchases should stay visible and editable.

  Scenario: View recurring reminders from sample rows
    Given the budget tracker API is mocked with sample recurring rows
      | id | category | description    | amount | entry_type | frequency | start_date | active |
      | 1  | Housing  | Rent           | 700.00 | expense    | monthly   | 2026-03-01 | true   |
      | 2  | Travel   | Weekly commute | 45.00  | expense    | weekly    | 2026-03-24 | true   |
    When I request all recurring reminders
    Then the latest collection should contain the text "Weekly commute"
    When I request the recurring calendar
    Then the latest result should contain the text "2026-03-24"

  Scenario: Add a recurring reminder
    Given the budget tracker API is mocked
    When I create a recurring reminder in category "Health" described as "Gym" amount "32.00" frequency "monthly" starting "2026-04-01"
    Then the latest result should contain the text "Gym"

  Scenario: Update a recurring reminder
    Given the budget tracker API is mocked
    When I update recurring reminder "1" to category "Housing" description "Updated rent" amount "720.00" frequency "monthly" start date "2026-03-01"
    Then the latest result should contain the text "Updated rent"
