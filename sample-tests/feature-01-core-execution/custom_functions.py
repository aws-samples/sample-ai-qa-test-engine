"""Custom functions for test execution.

These functions can be called from Gherkin steps using function call syntax.
Ported from test_translator/custom_functions_sample.py.
"""


def calculate_travel_cost(base_price: float, distance_multiplier: float) -> float:
    """Calculate travel cost based on base price and distance multiplier."""
    return base_price * distance_multiplier


def format_destination_info(destination_name: str, mass: str) -> str:
    """Format destination information as a readable string."""
    return f"Destination: {destination_name}, Mass: {mass}"


def verify_page_contains_text(text: str, nova_act) -> bool:
    """Verify that the current page contains specific text.

    Uses the reserved `nova_act` parameter for page inspection.
    """
    result = nova_act.expect(f"The text '{text}' is visible on the page").as_boolean()
    return result


def get_extracted_variable(variable_name: str, context: dict) -> str:
    """Get a previously extracted variable from the context.

    Uses the reserved `context` parameter.
    """
    variables = context.get('variables', {})
    if variable_name not in variables:
        raise ValueError(f"Variable '{variable_name}' not found in context")
    return str(variables[variable_name])


# --- Multi-value return examples ---


def get_destination_stats(destination: str) -> dict:
    """Return multiple stats as a dict — auto-unpacked to ${key.field}.

    Example Gherkin:
        When I call 'get_destination_stats' with destination "Proxima Centauri b" and store as "stats"
        Then "${stats.gravity}" should equal "1.1g"
        And "${stats.distance}" should equal "4.24 ly"
    """
    data = {
        "Proxima Centauri b": {"gravity": "1.1g", "distance": "4.24 ly", "price": "847K"},
        "Ross 128 b": {"gravity": "1.0g", "distance": "11 ly", "price": "890K"},
        "TRAPPIST-1e": {"gravity": "0.9g", "distance": "40 ly", "price": "1200K"},
    }
    return data.get(destination, {"gravity": "unknown", "distance": "unknown", "price": "unknown"})


def get_credentials(env: str = "test") -> tuple:
    """Return username and password as a tuple — use 'store as "user, pass"'.

    Example Gherkin:
        When I call 'get_credentials' with env "test" and store as "username, password"
        Then "${username}" should equal "testuser@example.com"
    """
    creds = {
        "test": ("testuser@example.com", "test_pass_123"),
        "staging": ("staging_user@example.com", "staging_pass_456"),
    }
    return creds.get(env, ("unknown", "unknown"))
