@NextDotGym
Feature: Intentional Failure Test
  This test has a step that will fail to demonstrate --stop-on-failure

  Scenario: Navigate then fail on wrong assertion
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations
    #replace the below "Mars" with "Proxima Centauri b" and the test will pass
    Then I should see the destination name "Mars"
