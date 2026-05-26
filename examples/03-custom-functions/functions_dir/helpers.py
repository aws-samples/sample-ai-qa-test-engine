"""Helper utilities — imported by main_functions.py.

Demonstrates cross-file imports when using --functions-file ./functions_dir/
"""


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def format_currency(amount: float, symbol: str = "¢") -> str:
    """Format a number as currency."""
    return f"{symbol} {amount:,.0f}"
