Feature: Local AI finance agent
  The user should be able to run the local Ollama finance briefing workflow from the dashboard.

  Scenario: Run the local finance agent
    Given the budget tracker API is mocked
    When I open the budget tracker homepage
    And I click the button "Run local agent"
    Then I should see the text "Local finance briefing"
    And I should see the text "Email draft"
