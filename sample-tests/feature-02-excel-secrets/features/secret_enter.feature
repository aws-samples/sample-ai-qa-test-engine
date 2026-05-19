@AmazonLogin
Feature: Amazon Login with Secrets Test
  As a tester
  I want to verify credential typing works on auth pages
  So that I can test login flows where Nova Act guardrails block direct typing

  # Demonstrates:
  # - "I enter X for username/password" auto-maps to enter_username/enter_password functions
  # - These use Playwright typing (bypasses Nova Act guardrails on auth pages)
  # - Secrets can be fetched from .env or AWS Secrets Manager via ${secret:name} or get_secret

  Scenario: Type email on Amazon sign-in page using natural syntax
    Given I am on the Amazon sign-in page
    And I enter "fakeuser_test_99999@example.com" for username
    And I click the Continue button
    Then I should see a page about creating a new account or that this email is new to Amazon

  Scenario: Type email using secret variable
    Given I call 'get_secret' with secret_name "TEST_EMAIL" and store as 'email'
    And I am on the Amazon sign-in page
    And I enter "${email}" for username
    And I click the Continue button
    Then I should see a page about creating a new account or that this email is new to Amazon
