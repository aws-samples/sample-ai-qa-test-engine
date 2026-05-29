@NextDotGym
Feature: Excel Data Loading
  As a tester
  I want to load test data from Excel files
  So that I can drive tests with external data

  Background:
    Given I am on the home page
    When I navigate to the destinations section

  Scenario: Load destination from Excel and verify
    When I call 'load_excel_field' with file "TestData.xlsx" and sheet "Destinations" and field "destination" and row 1 and store as 'dest_name'
    And I select "${dest_name}" from the destinations
    Then I should see the destination name "${dest_name}"
