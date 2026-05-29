@NextDotGym
Feature: Trajectory replay caching
  Verify that trajectories are recorded on first run and replayed on subsequent runs.
  Instruction steps (navigate, click) are cached; extraction/validation steps always use AI.

  # First run: records trajectories
  # Second run: replays instruction steps from cache (faster, no AI model calls)
  # --no-cache: disables replay, always uses Nova Act
  # --trajectory-strict: fails if page state differs during replay
  # @no-cache on a step: skips cache for that specific step

  Scenario: Browse destination details and verify planetary data
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations
    Then I should see the destination name "Proxima Centauri b"
    And the gravity information should show "1.1g"

  Scenario: Navigate across multiple pages
    Given I am on the home page
    When I click on "Destinations" in the navigation
    Then I should see a list of available destinations
    When I select "Ross 128 b" from the destinations
    Then I should see the destination name "Ross 128 b"

  Scenario: Steps with @no-cache bypass trajectory replay
    Given I am on the home page
    When I navigate to the destinations section @no-cache
    Then I should see a list of available destinations
    When I select "TRAPPIST-1e" from the destinations @no-cache
    Then I should see the destination name "TRAPPIST-1e"
