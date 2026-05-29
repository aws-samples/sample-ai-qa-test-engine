"""Exceptions for AI QA Test Engine.

Ported from test_translator/config/exceptions.py.
"""


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class TranslationError(Exception):
    """Raised when feature translation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)



