# Feature 4: Trajectory Replay Caching
# Tests that trajectory recording and replay works correctly.
#
# How to test:
#   1. First run (records trajectories):
#      ai-qa-test run --feature-dir ./features/ --env-file .env --tag-url-map-file ./tag-url-mapping.json
#
#   2. Second run (replays from cache — no AI model calls for action steps):
#      ai-qa-test run --feature-dir ./features/ --env-file .env --tag-url-map-file ./tag-url-mapping.json
#
#   3. Force fresh execution (bypass cache):
#      ai-qa-test run --feature-dir ./features/ --env-file .env --tag-url-map-file ./tag-url-mapping.json --no-cache
#
#   4. Strict replay validation (fail if page state differs):
#      ai-qa-test run --feature-dir ./features/ --env-file .env --tag-url-map-file ./tag-url-mapping.json --trajectory-strict

@nextdotgym
Feature: Trajectory replay caching
  Verify that trajectories are recorded on first run and replayed on subsequent runs.
  Uses multi-step flows across different pages to exercise trajectory caching.

  Scenario: Browse destination details and verify planetary data
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations
    Then I should see the destination name "Proxima Centauri b"
    And the gravity information should show "1.1g"
    And the atmosphere pressure should be displayed
    And the oxygen content should contain "19%"
    When I scroll down to the colony life section
    Then the population information should contain "234,000"

  Scenario: Book a journey search flow
    Given I am on the home page
    When I click on "Book Your Journey" in the navigation
    Then I should see the flight search form
    And I should see "7 BOOKABLE DESTINATIONS" displayed
    When I select "Proxima Centauri b" as the destination
    And I select "Earth - Terminal 1" as the origin
    Then the search form should have both origin and destination filled

  Scenario: Navigate across multiple pages
    Given I am on the home page
    When I click on "Why Go" in the navigation
    Then I should see "The Adventure of a Lifetime" heading
    And I should see the stat "99.7% SAFE ARRIVAL RATE"
    When I click on "Destinations" in the navigation
    Then I should see a list of available destinations
    When I select "Ross 128 b" from the destinations
    Then I should see the destination name "Ross 128 b"
    And the travel time should be displayed

  Scenario: Steps with @no-cache bypass trajectory replay
    Given I am on the home page
    When I navigate to the destinations section @no-cache
    Then I should see a list of available destinations
    When I select "TRAPPIST-1e" from the destinations @no-cache
    Then I should see the destination name "TRAPPIST-1e"
    And the starting price should show "1200 K"
