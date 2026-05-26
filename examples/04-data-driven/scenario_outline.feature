@NextDotGym
Feature: Scenario Outline
  As a tester
  I want to run the same scenario with different data
  So that I can test multiple destinations efficiently

  Scenario Outline: View different destinations
    Given I am on the home page
    When I navigate to the destinations section
    And I select "<destination>" from the destinations
    Then I should see the destination name "<destination>"

    Examples:
      | destination       |
      | Proxima Centauri b |
      | Ross 128 b         |
