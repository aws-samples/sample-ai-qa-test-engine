@NextDotGym
Feature: Input Variables
  As a tester
  I want to pre-load variables from a JSON file
  So that I can parameterize tests without hardcoding values

  # Run with: ai-qa-test run --feature-dir ./input_variables.feature \
  #   --variables-file ./input_vars.json \
  #   --tag-url-map-file ./tag-url-mapping.json --browser-mode headless
  #
  # input_vars.json contains:
  #   {"target_destination": "Proxima Centauri b", "expected_gravity": "1.1g", "expected_distance": "4.24 light-years"}

  Background:
    Given I am on the home page
    When I navigate to the destinations section

  Scenario: Use pre-loaded variables to select and verify destination
    When I select "${target_destination}" from the destinations
    Then I should see the destination name "${target_destination}"
    And the gravity information should contain "${expected_gravity}"
    And the distance should contain "${expected_distance}"
