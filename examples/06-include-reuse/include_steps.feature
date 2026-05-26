@NextDotGym
Feature: Common Steps Include
  As a tester
  I want to reuse common step sequences
  So that I don't repeat navigation steps in every feature

  Scenario: Use included steps to navigate then validate
    And @include "navigate_to_destination"
    Then I should see the destination name "Proxima Centauri b"
    And the mass information should be displayed
