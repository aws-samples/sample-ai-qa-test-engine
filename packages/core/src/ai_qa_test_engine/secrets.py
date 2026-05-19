"""Secrets management for test execution.

Supports fetching secrets from:
1. AWS Secrets Manager (production/CI)
2. Local .env file (development fallback)

Secrets are injectable into Gherkin steps via ${secret:secret_name} syntax
or via custom function calls.
"""

import json
import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


class SecretsManager:
    """Unified secrets access with AWS Secrets Manager + local .env fallback."""

    def __init__(self, region: str = "us-east-1", use_aws: bool = True):
        """Initialize secrets manager.

        Args:
            region: AWS region for Secrets Manager
            use_aws: Whether to attempt AWS Secrets Manager (False = .env only)
        """
        self._region = region
        self._use_aws = use_aws
        self._client = None
        self._cache: dict[str, Any] = {}

    def _get_client(self):
        """Lazy-init boto3 Secrets Manager client."""
        if self._client is None and self._use_aws:
            try:
                import boto3
                self._client = boto3.client(
                    "secretsmanager", region_name=self._region
                )
            except Exception as e:
                logger.warning(f"Could not create Secrets Manager client: {e}")
                self._use_aws = False
        return self._client

    def get_secret(self, secret_name: str) -> str:
        """Get a secret value by name.

        Lookup order:
        1. Local cache (already fetched this session)
        2. Environment variable (local .env fallback)
        3. AWS Secrets Manager

        Args:
            secret_name: Name/key of the secret

        Returns:
            Secret value as string

        Raises:
            KeyError: If secret not found in any source
        """
        # Check cache
        if secret_name in self._cache:
            return self._cache[secret_name]

        # Check environment variable (local .env fallback)
        env_value = os.environ.get(secret_name) or os.environ.get(secret_name.upper())
        if env_value:
            self._cache[secret_name] = env_value
            return env_value

        # Try AWS Secrets Manager
        if self._use_aws:
            client = self._get_client()
            if client:
                try:
                    response = client.get_secret_value(SecretId=secret_name)
                    secret_string = response.get("SecretString", "")

                    # Try to parse as JSON (common pattern: {"key": "value"})
                    try:
                        secret_dict = json.loads(secret_string)
                        # If it's a dict, cache all key-value pairs
                        if isinstance(secret_dict, dict):
                            for k, v in secret_dict.items():
                                self._cache[k] = str(v)
                            # Return the full JSON if the name matches the secret ID
                            if secret_name in secret_dict:
                                return str(secret_dict[secret_name])
                            return secret_string
                    except json.JSONDecodeError:
                        pass

                    # Plain string secret
                    self._cache[secret_name] = secret_string
                    return secret_string

                except client.exceptions.ResourceNotFoundException:
                    logger.debug(f"Secret '{secret_name}' not found in Secrets Manager")
                except Exception as e:
                    logger.warning(f"Error fetching secret '{secret_name}': {e}")

        raise KeyError(
            f"Secret '{secret_name}' not found. "
            f"Checked: environment variables, "
            f"{'AWS Secrets Manager' if self._use_aws else '.env only (AWS disabled)'}"
        )

    def get_secret_json(self, secret_name: str) -> dict:
        """Get a secret and parse it as JSON.

        Common pattern for secrets that contain multiple key-value pairs.

        Args:
            secret_name: Name/key of the secret in Secrets Manager

        Returns:
            Parsed JSON dictionary

        Raises:
            KeyError: If secret not found
            ValueError: If secret is not valid JSON
        """
        value = self.get_secret(secret_name)
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Secret '{secret_name}' is not valid JSON: {e}")

    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()
