@NextDotGym
Feature: Basic Navigation
  As a space traveler
  I want to navigate the Next Dot travel site
  So that I can browse available destinations

  @smoke @id:TC-NAV-001
  Scenario: Navigate to destinations page
    Given I am on the home page
    When I navigate to the destinations section
    Then I should see a list of available destinations
