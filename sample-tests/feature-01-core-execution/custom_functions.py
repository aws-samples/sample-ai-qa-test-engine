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
