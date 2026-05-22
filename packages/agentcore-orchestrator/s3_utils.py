"""S3 utility functions for the Orchestrator agent."""

import logging
import os
from datetime import datetime
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
s3_client = boto3.client("s3", region_name=AWS_REGION)


def list_objects(bucket: str, prefix: str, suffix: str = "") -> list[dict]:
    """List objects in S3 with optional suffix filter."""
    objects = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if suffix and not obj["Key"].endswith(suffix):
                continue
            objects.append({
                "key": obj["Key"],
                "last_modified": obj["LastModified"],
                "size": obj["Size"],
            })
    return objects


def get_last_modified(bucket: str, key: str) -> Optional[datetime]:
    """Get LastModified timestamp for an S3 object. Returns None if not found."""
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return response["LastModified"]
    except s3_client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return None
        raise


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
