"""Gherkin parser — parses .feature files into AST.

Extracted from test_translator/translator/agent.py::parse_gherkin_file.
Supports @include directive for reusable step groups.
"""

import re
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

    With the contents of the referenced step group file (e.g., common_steps/login_flow.steps).

    Args:
        content: Raw .feature file content
        common_steps_dir: Directory containing .steps files

    Returns:
        Content with @include directives expanded
    """
    if common_steps_dir is None or not common_steps_dir.exists():
        return content

    # Pattern: any keyword followed by @include "name"
    # e.g., "    And @include \"login_flow\""
    include_pattern = re.compile(
        r'^(\s*)(Given|When|Then|And|But)\s+@include\s+"([^"]+)"',
        re.MULTILINE,
    )

    def replace_include(match):
        indent = match.group(1)
        # keyword is not used — included steps have their own keywords
        include_name = match.group(3)

        # Look for the .steps file
        steps_file = common_steps_dir / f"{include_name}.steps"
        if not steps_file.exists():
            raise FileNotFoundError(
                f"Common steps file not found: {steps_file}\n"
                f"Referenced by @include \"{include_name}\""
            )

        # Read and indent the steps content
        steps_content = steps_file.read_text().strip()

        # Indent each line to match the original indentation
        indented_lines = []
        for line in steps_content.splitlines():
            if line.strip():
                indented_lines.append(f"{indent}{line.strip()}")
            else:
                indented_lines.append("")

        return "\n".join(indented_lines)

    # Resolve includes (support nested includes up to 5 levels)
    for _ in range(5):
        new_content = include_pattern.sub(replace_include, content)
        if new_content == content:
            break
        content = new_content

    return content


def preprocess_feature_file(file_path: Path, common_steps_dir: Path | None = None) -> str:
    """Read a feature file and preprocess it (resolve @includes).

    Args:
        file_path: Path to the .feature file
        common_steps_dir: Directory containing .steps files

    Returns:
        Preprocessed feature file content (ready for gherkin parser)
    """
    content = file_path.read_text()
    return resolve_includes(content, common_steps_dir)
