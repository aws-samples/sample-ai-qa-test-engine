@NextDotGym
Feature: Screenshot + Claude Extraction
  As a tester
  I want to extract data from screenshots using Claude
  So that I can capture complex visual information

  Background:
    Given I am on the home page
    When I navigate to the destinations section
    And I select "Proxima Centauri b" from the destinations

  Scenario: Extract destination name from screenshot
    When I call 'extract_from_screenshot' with prompt "What is the name of the destination/planet shown on this page?" and store as 'extracted_name'
    Then I should see the destination name "${extracted_name}"
