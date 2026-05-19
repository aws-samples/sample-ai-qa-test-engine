@NextDotGym
Feature: Data Tables
  As a tester
  I want to use data tables in my steps
  So that I can pass structured data to actions

  Background:
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations

  Scenario: Verify multiple destination attributes are displayed
    Then the following information should be visible on the page:
      | attribute   |
      | mass        |
      | temperature |
      | gravity     |
