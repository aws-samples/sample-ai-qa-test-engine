"""Main functions that import from helpers.py.

Demonstrates cross-file imports when using --functions-file ./functions_dir/
The directory is added to sys.path, so 'from helpers import ...' works.
"""

from helpers import multiply, format_currency


def calculate_trip_total(base_price: float, passengers: float, tax_rate: float = 0.1) -> dict:
    """Calculate trip total with tax — returns dict for auto-unpack.

    Example Gherkin:
        When I call 'calculate_trip_total' with base_price 1000 and passengers 2 and store as "trip"
        Then "${trip.subtotal}" should equal "2000.0"
        And "${trip.tax}" should equal "200.0"
        And "${trip.total}" should equal "2200.0"
    """
    subtotal = multiply(base_price, passengers)
    tax = multiply(subtotal, tax_rate)
    total = subtotal + tax
    return {
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "formatted": format_currency(total),
    }


def get_booking_info(destination: str) -> tuple:
    """Return booking reference and confirmation code as tuple.

    Example Gherkin:
        When I call 'get_booking_info' with destination "Mars" and store as "ref, code"
    """
    # Simulated booking
    ref = f"BK-{destination[:3].upper()}-001"
    code = f"CONF-{hash(destination) % 10000:04d}"
    return (ref, code)
