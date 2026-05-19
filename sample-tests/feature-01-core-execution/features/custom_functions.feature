@NextDotGym
Feature: Custom Functions
  As a tester
  I want to call custom Python functions from Gherkin steps
  So that I can perform calculations and data transformations

  Background:
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations

  Scenario: Calculate travel cost using custom function
    When I extract the destination name and store it as "destination_name"
    And I extract the mass as a string and store it as "mass_info"
    And I call 'format_destination_info' with destination_name "${destination_name}" and mass "${mass_info}" and store as 'formatted_info'
    And I call 'calculate_travel_cost' with base_price 1000 and distance_multiplier 4.2 and store as 'total_cost'
    Then the mass information should be displayed
