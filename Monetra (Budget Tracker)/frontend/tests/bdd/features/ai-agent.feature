Feature: AI finance agent
  The finance briefing workflow should return a completed analysis packet.

  Scenario: Run the finance agent
    Given the budget tracker API is mocked
    When I run a finance briefing for "Prepare a finance briefing"
    Then the latest result should have status "completed"
    And the latest result should contain the text "Finance briefing"
    And the latest result should contain the text "Monthly briefing attached."
    And the latest result should contain the text "Keep monitoring travel costs."

