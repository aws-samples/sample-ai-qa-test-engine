@NextDotGym
Feature: Data Extraction
  As a tester
  I want to extract data from pages
  So that I can use it in subsequent steps

  Background:
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations

  @id:TC-EXT-001
  Scenario: Extract and verify destination name
    When I extract the destination name and store it as "destination_name"
    Then I should see the destination name matches "${destination_name}"

  @id:TC-EXT-002
  Scenario: Extract multiple values
    When I extract the destination name and store it as "destination_name"
    And I extract the mass as a string and store it as "mass_info"
    Then the mass information should be displayed
