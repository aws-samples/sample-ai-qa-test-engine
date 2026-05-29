"""Excel data loading as a custom function.

Usage in Gherkin:
    Given I call 'load_excel_data' with file "TestData.xlsx" and sheet "Login" and row 1 and store as 'login_data'

Or for loading individual fields:
    Given I call 'load_excel_field' with file "TestData.xlsx" and sheet "Login" and row 1 and field "username" and store as 'username'
"""

from pathlib import Path
from typing import Any


def load_excel_data(file: str, sheet: str, row: int = 1, context: dict = None) -> dict:
    """Load a row of data from an Excel file.

    All column values become accessible. The returned dict can be stored
    and individual fields accessed via subsequent function calls.

    Args:
        file: Path to Excel file (relative to working directory)
        sheet: Sheet name to read from
        row: Row number (1-indexed, excluding header row)
        context: Execution context (injected automatically)

    Returns:
        Dictionary of column_name → value
    """
    from ai_qa_test_engine.excel_reader import read_excel_data

    file_path = Path(file)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    # Fallback: if full relative path doesn't exist, try just the filename
    # (handles AgentCore mode where files are downloaded flat to a temp dir)
    if not file_path.exists():
        basename_path = Path.cwd() / Path(file).name
        if basename_path.exists():
            file_path = basename_path

    data = read_excel_data(file_path, sheet, row=row)
    return data


def load_excel_field(file: str, sheet: str, field: str, row: int = 1) -> str:
    """Load a single field from an Excel file.

    Args:
        file: Path to Excel file
        sheet: Sheet name
        field: Column name (header) to extract
        row: Row number (1-indexed, excluding header)

    Returns:
        Cell value as string
    """
    from ai_qa_test_engine.excel_reader import read_excel_data

    file_path = Path(file)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    data = read_excel_data(file_path, sheet, row=row)

    # Normalize field name for lookup
    normalized_field = field.strip().lower().replace(" ", "_")
    if normalized_field not in data:
        available = list(data.keys())
        raise ValueError(
            f"Field '{field}' (normalized: '{normalized_field}') not found. "
            f"Available fields: {available}"
        )

    return str(data[normalized_field])


def get_secret(secret_name: str, context: dict = None) -> str:
    """Fetch a secret from AWS Secrets Manager or local .env.

    Args:
        secret_name: Name of the secret to fetch
        context: Execution context (injected automatically)

    Returns:
        Secret value as string
    """
    from ai_qa_test_engine.secrets import SecretsManager

    manager = SecretsManager()
    return manager.get_secret(secret_name)
