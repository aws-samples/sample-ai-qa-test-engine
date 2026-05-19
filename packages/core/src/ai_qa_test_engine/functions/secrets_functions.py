"""Secrets functions for secure credential handling in tests.

Passwords and sensitive data are typed via Playwright directly (not Nova Act)
so they don't appear in Nova Act trajectory logs or recordings.

Usage in Gherkin:
    When I call 'get_secret' with secret_name "LOGIN_PASSWORD" and store as 'password'
    And I call 'type_secret' with value "${password}" and field_prompt "Click on the password field"

Or combined (fetch + type in one step):
    When I call 'type_secret_from_store' with secret_name "LOGIN_PASSWORD" and field_prompt "Click on the password field"
"""

from ai_qa_test_engine.secrets import SecretsManager


def get_secret(secret_name: str, context: dict = None) -> str:
    """Fetch a secret from AWS Secrets Manager or local .env.

    Args:
        secret_name: Name of the secret to fetch
        context: Execution context (injected automatically)

    Returns:
        Secret value as string
    """
    manager = SecretsManager()
    return manager.get_secret(secret_name)


def type_secret(value: str, field_prompt: str, nova_act=None) -> None:
    """Type a secret value into a field using Playwright directly.

    Uses Nova Act to focus/click the field, then Playwright keyboard.type()
    to enter the value without it appearing in Nova Act logs.

    Args:
        value: The secret value to type
        field_prompt: Nova Act prompt to click/focus the field (e.g., "Click on the password field")
        nova_act: Nova Act instance (injected automatically)

    Example Gherkin:
        And I call 'type_secret' with value "${password}" and field_prompt "Click on the password field"
    """
    if nova_act is None:
        raise RuntimeError("type_secret requires nova_act (must be called from a test step)")

    # Use Nova Act to click/focus the field
    nova_act.act(field_prompt)

    # Type the secret directly via Playwright (bypasses Nova Act logging)
    page = nova_act.get_page()
    page.keyboard.type(value)


def type_secret_from_store(secret_name: str, field_prompt: str, nova_act=None) -> None:
    """Fetch a secret and type it into a field in one step.

    Combines get_secret + type_secret for convenience.

    Args:
        secret_name: Name of the secret to fetch
        field_prompt: Nova Act prompt to click/focus the field
        nova_act: Nova Act instance (injected automatically)

    Example Gherkin:
        And I call 'type_secret_from_store' with secret_name "LOGIN_PASSWORD" and field_prompt "Click on the password field"
    """
    value = get_secret(secret_name)
    type_secret(value=value, field_prompt=field_prompt, nova_act=nova_act)


def fill_field_secure(selector: str, value: str, nova_act=None) -> None:
    """Fill a field by CSS selector using Playwright directly.

    Alternative to type_secret when you know the exact CSS selector.

    Args:
        selector: CSS selector for the input field
        value: Value to fill
        nova_act: Nova Act instance (injected automatically)

    Example Gherkin:
        And I call 'fill_field_secure' with selector "#password" and value "${password}"
    """
    if nova_act is None:
        raise RuntimeError("fill_field_secure requires nova_act")

    page = nova_act.get_page()
    page.fill(selector, value)
