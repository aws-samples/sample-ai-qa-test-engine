@NextDotGym
Feature: Input Variables
  As a tester
  I want to pre-load variables from a JSON file
  So that I can parameterize tests without hardcoding values

  # Run with: ai-qa-test run --feature-dir . --variables-file ./input_vars.json \
  #   --tag-url-map-file ./tag-url-mapping.json

  # input_vars.json supports nested objects:
  # {"target": {"destination": "Proxima Centauri b", "expected_gravity": "1.1g"}}
  # Access via dotted notation: ${target.destination}, ${target.expected_gravity}

  Background:
    Given I am on the home page
    When I navigate to the destinations section

  Scenario: Use pre-loaded nested variable to select destination
    When I select "${target.destination}" from the destinations
    Then I should see the destination name "${target.destination}"
