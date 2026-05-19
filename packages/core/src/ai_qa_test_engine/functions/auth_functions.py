"""Authentication helper functions for login flows.

These handle the common pattern of typing credentials on auth pages
where Nova Act guardrails block direct act() typing.

Usage in Gherkin (natural language — translator auto-maps these):
    And I enter "user@example.com" for username
    And I enter "mypassword" for password
    And I enter "${secret_password}" for password

These get translated to function_call steps automatically by the system prompt.
"""


def enter_username(value: str, nova_act=None) -> None:
    """Type a username/email into the currently visible username/email field.

    Uses Nova Act to focus the field, then Playwright to type (bypasses guardrails).

    Args:
        value: The username/email to type
        nova_act: Nova Act instance (injected automatically)
    """
    if nova_act is None:
        raise RuntimeError("enter_username requires nova_act")

    # Use Nova Act to focus the username/email field
    nova_act.act("Click on the username or email input field")

    # Type via Playwright directly (bypasses Nova Act logging/guardrails)
    page = nova_act.get_page()
    page.keyboard.type(value)


def enter_password(value: str, nova_act=None) -> None:
    """Type a password into the currently visible password field.

    Uses Nova Act to focus the field, then Playwright to type (bypasses guardrails).

    Args:
        value: The password to type
        nova_act: Nova Act instance (injected automatically)
    """
    if nova_act is None:
        raise RuntimeError("enter_password requires nova_act")

    # Use Nova Act to focus the password field
    nova_act.act("Click on the password input field")

    # Type via Playwright directly
    page = nova_act.get_page()
    page.keyboard.type(value)
