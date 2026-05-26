"""Scenario ID generation — canonical unique identifier for each scenario.

Priority:
1. @id:XXX tag on the scenario (user-defined, explicit)
2. Fallback: {filename}__{feature_slug}__{scenario_slug}

Used for:
- Nova Act workflow definition name
- Extracted variables file naming
- S3 result paths
- Trajectory cache keys
"""

import re
from typing import Optional


def slugify(text: str, max_len: int = 0) -> str:
    """Convert text to a safe slug (lowercase, alphanumeric + underscores).

    Args:
        text: Input text
        max_len: Maximum length (0 = no limit)

    Returns:
        Safe slug string
    """
    slug = re.sub(r"[^\w]+", "_", text).strip("_").lower()
    if max_len > 0:
        slug = slug[:max_len]
    return slug.rstrip("_")


def extract_id_tag(tags: list[str] | None) -> Optional[str]:
    """Extract @id:XXX from scenario tags.

    Args:
        tags: List of tags (e.g., ["@smoke", "@id:TC-001"])

    Returns:
        The ID value (e.g., "TC-001") or None if no @id tag
    """
    if not tags:
        return None
    for tag in tags:
        # Support @id:XXX or @id=XXX
        tag_clean = tag.lstrip("@")
        if tag_clean.startswith("id:") or tag_clean.startswith("id="):
            return tag_clean[3:]
    return None


def make_scenario_id(
    feature_name: str,
    scenario_name: str,
    filename: str = "",
    tags: list[str] | None = None,
) -> str:
    """Generate a canonical scenario ID.

    Priority:
    1. @id:XXX tag → use that directly
    2. Fallback: {filename}__{feature_slug}__{scenario_slug}

    Args:
        feature_name: Feature name (from Feature: line)
        scenario_name: Scenario name (from Scenario: line)
        filename: Source .feature filename (without extension)
        tags: Scenario-level tags (checked for @id:XXX)

    Returns:
        Canonical scenario ID string (safe for file paths, S3 keys, workflow names)
    """
    # Check for explicit @id tag
    explicit_id = extract_id_tag(tags)
    if explicit_id:
        return slugify(explicit_id)

    # Fallback: filename__feature__scenario
    parts = []
    if filename:
        parts.append(slugify(filename, max_len=30))
    parts.append(slugify(feature_name, max_len=30))
    parts.append(slugify(scenario_name, max_len=40))

    return "__".join(parts)


def make_workflow_name(scenario_id: str) -> str:
    """Derive Nova Act workflow definition name from scenario ID.

    Nova Act limit: 40 chars, pattern [a-zA-Z][a-zA-Z0-9_-]{0,39}

    Args:
        scenario_id: Canonical scenario ID

    Returns:
        Workflow definition name (max 40 chars)
    """
    # Prefix with "tt-" (test translator), convert underscores to hyphens
    name = f"tt-{scenario_id}".replace("__", "-").replace("_", "-")
    # Ensure starts with letter and only valid chars
    name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    return name[:40]
