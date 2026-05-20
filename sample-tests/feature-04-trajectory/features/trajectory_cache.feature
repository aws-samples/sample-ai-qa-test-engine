# Feature 4: Trajectory Replay Caching
# Tests that trajectory recording and replay works correctly.
#
# How to test:
#   1. First run (records trajectories):
#      ai-qa-test run --feature-dir ./features/ --env-file ../.env --tag-url-map-file ../tag-url-mapping.json
#
#   2. Second run (replays from cache — no AI model calls for action steps):
#      ai-qa-test run --feature-dir ./features/ --env-file ../.env --tag-url-map-file ../tag-url-mapping.json
#
#   3. Force fresh execution (bypass cache):
#      ai-qa-test run --feature-dir ./features/ --env-file ../.env --tag-url-map-file ../tag-url-mapping.json --no-cache
#
#   4. Strict replay validation (fail if page state differs):
#      ai-qa-test run --feature-dir ./features/ --env-file ../.env --tag-url-map-file ../tag-url-mapping.json --trajectory-strict

@nextdotgym
Feature: Trajectory replay caching
  Verify that trajectories are recorded on first run and replayed on subsequent runs.

  Scenario: Navigate and verify with trajectory caching
    Given I am on the Next Dot Gym homepage
    When I click on the Destinations page
    Then I should see a list of destinations

  Scenario: Navigate with @no-cache step
    Given I am on the Next Dot Gym homepage
    When I click on the Destinations page @no-cache
    Then I should see a list of destinations
