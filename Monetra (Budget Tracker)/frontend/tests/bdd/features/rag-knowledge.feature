Feature: RAG finance knowledge base
  The user should be able to query and refresh the finance knowledge base separately from the action agent.

  Scenario: Ask the semantic finance knowledge base a grounded question
    Given the budget tracker API is mocked
    When I ask the finance knowledge base "What is putting pressure on cash flow this month?"
    Then the latest result should contain the text "Housing and groceries are the main pressure points this month"
    And the latest result should contain the text "Financial pulse"
    And the latest result should contain 2 sources

  Scenario: Reindex the finance knowledge base
    Given the budget tracker API is mocked
    When I reindex the finance knowledge base
    Then the latest result should contain the text "14"
    And the latest result should contain the text "bdd-signature-2"
