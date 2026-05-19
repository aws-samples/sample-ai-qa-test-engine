"""Screenshot + Claude extraction utility function.

Takes a screenshot of the current page, sends it to Claude via Bedrock,
and extracts specified data from the image.

Usage in Gherkin:
    And I call 'extract_from_screenshot' with prompt "What is the order ID shown on the page?" and store as 'order_id'
    And I call 'extract_from_screenshot' with prompt "What is the email address displayed?" and store as 'email'
"""

import base64
import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)


def extract_from_screenshot(prompt: str, nova_act) -> str:
    """Take a screenshot and use Claude to extract data from it.

    This function:
    1. Takes a screenshot of the current browser page
    2. Sends the screenshot to Claude (via Bedrock) with the extraction prompt
    3. Returns the extracted text

    Args:
        prompt: What to extract from the screenshot (e.g., "What is the order ID?")
        nova_act: Nova Act browser instance (injected automatically via reserved param)

    Returns:
        Extracted text from the screenshot

    Raises:
        RuntimeError: If screenshot or Claude call fails
    """
    # Take screenshot
    try:
        page = nova_act.get_page()
        screenshot_bytes = page.screenshot()
    except Exception as e:
        raise RuntimeError(f"Failed to take screenshot: {e}")

    if not screenshot_bytes:
        raise RuntimeError("Screenshot returned empty bytes")

    # Call Claude via Bedrock
    region = os.environ.get("AWS_REGION", "us-east-1")
    model_id = os.environ.get(
        "CLAUDE_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )

    try:
        client = boto3.client("bedrock-runtime", region_name=region)

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": "png",
                            "source": {
                                "bytes": screenshot_bytes,
                            },
                        },
                    },
                    {
                        "text": (
                            f"{prompt}\n\n"
                            "Respond with ONLY the extracted value, nothing else. "
                            "No explanation, no quotes, no formatting — just the raw value."
                        ),
                    },
                ],
            }
        ]

        response = client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={"maxTokens": 256, "temperature": 0.0},
        )

        # Extract response text
        output = response["output"]["message"]["content"][0]["text"]
        result = output.strip()

        logger.info(f"Screenshot extraction: '{prompt}' → '{result}'")
        return result

    except Exception as e:
        raise RuntimeError(f"Claude extraction failed: {e}")


def extract_table_from_screenshot(prompt: str, nova_act) -> list[dict]:
    """Take a screenshot and use Claude to extract tabular data from it.

    Args:
        prompt: Description of what table to extract (e.g., "Extract the pricing table")
        nova_act: Nova Act browser instance (injected automatically)

    Returns:
        List of dictionaries representing table rows

    Raises:
        RuntimeError: If extraction fails
    """
    # Take screenshot
    try:
        page = nova_act.get_page()
        screenshot_bytes = page.screenshot()
    except Exception as e:
        raise RuntimeError(f"Failed to take screenshot: {e}")

    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    region = os.environ.get("AWS_REGION", "us-east-1")
    model_id = os.environ.get(
        "CLAUDE_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )

    try:
        client = boto3.client("bedrock-runtime", region_name=region)

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": "png",
                            "source": {
                                "bytes": screenshot_bytes,
                            },
                        },
                    },
                    {
                        "text": (
                            f"{prompt}\n\n"
                            "Extract the data as a JSON array of objects. "
                            "Use column headers as keys. "
                            "Respond with ONLY valid JSON, nothing else."
                        ),
                    },
                ],
            }
        ]

        response = client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={"maxTokens": 4096, "temperature": 0.0},
        )

        output = response["output"]["message"]["content"][0]["text"]
        result = json.loads(output.strip())

        logger.info(f"Table extraction: '{prompt}' → {len(result)} rows")
        return result

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude returned invalid JSON for table extraction: {e}")
    except Exception as e:
        raise RuntimeError(f"Claude table extraction failed: {e}")
