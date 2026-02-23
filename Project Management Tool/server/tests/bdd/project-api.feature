Feature: Project API behavior
  As a project manager
  I want project creation endpoints to enforce constraints
  So project data remains valid

  Scenario: Reject empty project name
    When I create a project with name "" and description "desc"
    Then the project API response status should be 400
    And the project API error should contain "Project name is required"

  Scenario: Create project successfully
    When I create a project with name "Portfolio Launch" and description "Go live preparation"
    Then the project API response status should be 201
    And the project payload should include name "Portfolio Launch"

  Scenario: Reject duplicate project name
    Given a project already exists with name "Duplicate Project"
    When I create a project with name "Duplicate Project" and description "duplicate"
    Then the project API response status should be 409
    And the project API error should contain "already exists"