Feature: Transaction management
  A finance user should be able to review, create, and search expense records.

  Scenario: View expense records from sample rows
    Given the budget tracker API is mocked with sample expense rows
      | id | date       | category | description | amount | entry_type |
      | 1  | 2026-03-01 | Food     | Groceries   | 20.50  | expense    |
      | 2  | 2026-03-02 | Salary   | Payroll     | 920.00 | income     |
    When I request all expenses
    Then the latest collection should contain the text "Payroll"

  Scenario: Add a new expense and find it later
    Given the budget tracker API is mocked
    When I create an expense dated "2026-03-02" in category "Travel" with description "Bus" and amount "4.20"
    Then the latest result should contain the text "Bus"
    When I request all expenses
    Then the latest collection should contain the text "Bus"

  Scenario: Search for a transaction by id
    Given the budget tracker API is mocked
    When I search for expense id "1"
    Then the latest result should contain the text "Groceries"
