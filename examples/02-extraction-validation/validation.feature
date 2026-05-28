@NextDotGym
Feature: Validation
  As a tester
  I want to validate page content
  So that I can verify the application works correctly

  Background:
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations

  @smoke @id:TC-VAL-001
  Scenario: Validate destination details are displayed
    Then I should see the destination name "Proxima Centauri b"
    And the mass information should be displayed
    And the temperature information should be displayed
    And the gravity information should be displayed
