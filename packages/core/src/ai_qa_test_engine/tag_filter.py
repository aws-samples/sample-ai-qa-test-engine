"""Tag-based scenario filtering.

Supports:
  @smoke              — include scenarios with @smoke tag
  @id:TC-001          — include specific scenario by ID
  not @slow           — exclude scenarios with @slow tag
  @smoke and @login   — include scenarios with both tags
  @smoke or @login    — include scenarios with either tag
"""

import re
from typing import List


def matches_tag_filter(scenario_tags: List[str], filter_expr: str) -> bool:
    """Check if a scenario's tags match a filter expression.

    Args:
        scenario_tags: Tags on the scenario (e.g., ["@smoke", "@id:TC-001"])
        filter_expr: Filter expression (e.g., "@smoke", "not @slow", "@smoke and @login")

    Returns:
        True if the scenario should be included
    """
    if not filter_expr or not filter_expr.strip():
        return True  # No filter = include all

    expr = filter_expr.strip()

    # Normalize scenario tags to lowercase for comparison
    normalized_tags = [t.lower().lstrip("@") for t in scenario_tags]

    # Handle "not @tag"
    if expr.lower().startswith("not "):
        tag = expr[4:].strip().lower().lstrip("@")
        return tag not in normalized_tags

    # Handle "tag1 and tag2"
    if " and " in expr.lower():
        parts = re.split(r"\s+and\s+", expr, flags=re.IGNORECASE)
        return all(_tag_matches(normalized_tags, p.strip()) for p in parts)

    # Handle "tag1 or tag2"
    if " or " in expr.lower():
        parts = re.split(r"\s+or\s+", expr, flags=re.IGNORECASE)
        return any(_tag_matches(normalized_tags, p.strip()) for p in parts)

    # Simple single tag match
    return _tag_matches(normalized_tags, expr)


def _tag_matches(normalized_tags: List[str], tag_expr: str) -> bool:
    """Check if a single tag expression matches the normalized tag list."""
    tag = tag_expr.lower().lstrip("@")

    # Exact match
    if tag in normalized_tags:
        return True

    # Check @id:XXX style (match against "id:xxx" in normalized tags)
    for t in normalized_tags:
        if t == tag or t == f"id:{tag}":
            return True

    return False


def filter_scenarios(scenarios: list, tag_filter: str) -> list:
    """Filter a list of scenarios by tag expression.

    Args:
        scenarios: List of TestScenario objects or dicts with 'tags' field
        tag_filter: Tag filter expression

    Returns:
        Filtered list of scenarios that match
    """
    if not tag_filter:
        return scenarios

    filtered = []
    for scenario in scenarios:
        tags = scenario.tags if hasattr(scenario, "tags") else scenario.get("tags", [])
        if matches_tag_filter(tags, tag_filter):
            filtered.append(scenario)

    return filtered
