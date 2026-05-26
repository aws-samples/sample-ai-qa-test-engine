@NextDotGym
Feature: Input Variables
  As a tester
  I want to pre-load variables from a JSON file
  So that I can parameterize tests without hardcoding values

  # Run with: ai-qa-test run --feature-dir ./features/input_variables.feature \
  #   --variables-file ./input_vars.json \
  #   --tag-url-map-file ./tag-url-mapping.json --browser-mode headless
  #
  # Where input_vars.json contains: {"target_destination": "Proxima Centauri b"}

  Background:
    Given I am on the home page
    When I navigate to the destinations section

  Scenario: Use pre-loaded variable to select destination
    When I select "${target_destination}" from the destinations
    Then I should see the destination name "${target_destination}"
