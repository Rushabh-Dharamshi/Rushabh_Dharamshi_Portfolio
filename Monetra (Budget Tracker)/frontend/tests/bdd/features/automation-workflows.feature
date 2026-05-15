Feature: Automation workflows
  The user should be able to run the predefined finance workflows from the automation center.

  Scenario: Run the month-end close workflow
    Given the budget tracker API is mocked
    When I run the workflow "month_end_close"
    Then the latest result should have status "completed"
    And the latest result should contain the text "Month-end pack ready"
    And the latest result should contain the text "Share the pack with stakeholders."
    When I request recent workflow runs
    Then the latest collection should contain the text "Month-end close"
