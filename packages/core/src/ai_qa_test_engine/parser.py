"""Gherkin parser — parses .feature files into AST.

Extracted from test_translator/translator/agent.py::parse_gherkin_file.
Adds @include resolution stub for Feature 3.
"""

from pathlib import Path

from gherkin.parser import Parser


def parse_gherkin_file(file_path: Path) -> dict:
    """Parse a .feature file into Gherkin AST.

    Args:
        file_path: Path to the .feature file

    Returns:
        Gherkin AST dictionary
    """
    parser = Parser()
    content = file_path.read_text()
    return parser.parse(content)


def resolve_includes(content: str, common_steps_dir: Path | None = None) -> str:
    """Resolve @include directives in feature file content.

    Replaces lines like:
        And @include "login_flow"

    With the contents of the referenced step group file.

    Args:
        content: Raw .feature file content
        common_steps_dir: Directory containing .steps files

    Returns:
        Content with @include directives expanded

    Note:
        This is a stub for Feature 3. Currently returns content unchanged.
    """
    # Feature 3: Will implement @include resolution
    # For now, pass through unchanged
    return content
