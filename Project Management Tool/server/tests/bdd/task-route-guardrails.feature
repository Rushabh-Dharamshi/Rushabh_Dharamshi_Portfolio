Feature: Task API guardrails
  As a project manager
  I want task route validations to be strict
  So invalid workflow transitions are blocked

  Scenario: Reject invalid status value
    Given a task exists with id 31 and progress 100
    When I change task status for id 31 to "qa_review"
    Then the API response status should be 400
    And the API error message should contain "status must be one of"
    And no task status update should be saved

  Scenario: Return not found when changing status for missing task
    Given task id 32 does not exist
    When I change task status for id 32 to "blocked"
    Then the API response status should be 404
    And the API error message should contain "Task not found"

  Scenario: Reject completion payload when boolean value is invalid
    Given a task exists with id 33 and progress 100
    When I change task completion for id 33 to "invalid_boolean"
    Then the API response status should be 400
    And the API error message should contain "is_completed must be a boolean"

  Scenario: Return not found when changing completion for missing task
    Given task id 34 does not exist
    When I change task completion for id 34 to "true"
    Then the API response status should be 404
    And the API error message should contain "Task not found"

  Scenario: Reject completion true below 100 progress
    Given a task exists with id 35 and progress 20
    When I change task completion for id 35 to "true"
    Then the API response status should be 400
    And the API error message should contain "marked completed only when progress is 100"
    And no task completion update should be saved

  Scenario: Accept completion true at 100 progress
    Given a task exists with id 36 and progress 100
    When I change task completion for id 36 to "true"
    Then the API response status should be 200
    And task completion update should be saved as "true"

  Scenario: Accept completion false at any progress
    Given a task exists with id 37 and progress 40
    When I change task completion for id 37 to "false"
    Then the API response status should be 200
    And task completion update should be saved as "false"