Feature: Transaction management
  A user should be able to review and work with transaction records quickly.

  Scenario: View transaction records from sample expense rows
    Given the budget tracker API is mocked with sample expense rows
      | id | date       | category | description | amount | entry_type |
      | 1  | 2026-03-01 | Food     | Groceries   | 20.50  | expense    |
      | 2  | 2026-03-02 | Salary   | Payroll     | 920.00 | income     |
    When I open the budget tracker homepage
    Then I should see the text "Transaction records"
    And I should see the text "Payroll"

  Scenario: Add a new transaction
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I fill the field "Date" with "2026-03-02"
    And I fill the placeholder "Housing, Travel, Food" with "Travel"
    And I fill the placeholder "Weekly groceries" with "Bus"
    And I fill the field "Amount (GBP)" with "4.20"
    And I click the button "Add transaction"
    Then I should see the text "Expense #3 added successfully."
    And I should see the text "Bus"

  Scenario: Search for a transaction by id
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I fill the placeholder "Search by ID" with "1"
    And I click the button "Search"
    Then I should see the text "Showing search result for expense #1."
