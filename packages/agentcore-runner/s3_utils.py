"""S3 utility functions for the Test Runner agent."""

import logging
import os
from datetime import datetime
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
s3_client = boto3.client("s3", region_name=AWS_REGION)


def download_file(bucket: str, key: str, local_path: str) -> str:
    """Download an S3 object to a local file."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    s3_client.download_file(bucket, key, local_path)
    return local_path


def download_string(bucket: str, key: str) -> str:
    """Download an S3 object as a string."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


def upload_string(content: str, bucket: str, key: str, content_type: str = "application/json") -> str:
    """Upload a string to S3."""
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType=content_type,
    )
    return key


def upload_file(local_path: str, bucket: str, key: str) -> str:
    """Upload a local file to S3."""
    s3_client.upload_file(local_path, bucket, key)
    return key
