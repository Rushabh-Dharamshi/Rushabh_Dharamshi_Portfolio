Feature: Local AI finance agent
  The local finance briefing workflow should return a completed analysis packet.

  Scenario: Run the local finance agent
    Given the budget tracker API is mocked
    When I run a local finance briefing for "Prepare a finance briefing"
    Then the latest result should have status "completed"
    And the latest result should contain the text "Local finance briefing"
    And the latest result should contain the text "Monthly briefing attached."
    And the latest result should contain the text "Keep monitoring travel costs."

