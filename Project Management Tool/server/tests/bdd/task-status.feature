Feature: Task status completion
  As a project manager
  I want done status to be allowed only at 100 percent progress
  So task boards reflect true completion

  Scenario: Reject done status when progress is below 100
    Given a task with id 21 and progress 80
    When I set the task status to "done"
    Then the API responds with status code 400
    And the response contains "Status can be set to done only when progress is 100"

  Scenario: Accept done status when progress is 100
    Given a task with id 22 and progress 100
    When I set the task status to "done"
    Then the API responds with status code 200
    And the task status update is persisted