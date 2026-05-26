@nextdotgym
Feature: Trajectory replay - destination details
  Verify trajectory recording on a multi-step destination browsing flow.

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
