# Tests multi-value function returns (dict and tuple unpacking)
#
# Run:
#   ai-qa-test run --feature-dir ./features/multi_value_functions.feature \
#     --functions-file ./custom_functions.py \
#     --tag-url-map-file ./tag-url-mapping.json

@NextDotGym
Feature: Multi-value function returns
  As a tester
  I want functions to return multiple values
  So that I can use individual fields in subsequent steps

  Background:
    Given I am on the home page
    When I navigate to the destinations section

  Scenario: Dict return — auto-unpack to ${key.field}
    When I call 'get_destination_stats' with destination "Proxima Centauri b" and store as "stats"
    And I select "Proxima Centauri b" from the destinations
    Then the gravity information should contain "${stats.gravity}"

  Scenario: Tuple return — positional unpack to separate variables
    When I call 'get_credentials' with env "test" and store as "username, password"
    Then I verify that "${username}" equals "testuser@example.com"
    And I verify that "${password}" equals "test_pass_123"
