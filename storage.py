import logging
import os
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

LOCAL_DIR = Path("artifacts")


def create_s3_client():
    """Build an S3 client. S3_ENDPOINT_URL points it at Backblaze B2; unset, it uses AWS.

    Credentials come from boto3's normal lookup, so this also works with AWS IAM
    roles, which never set AWS_ACCESS_KEY_ID.
    """
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
        config=Config(
            connect_timeout=5,
            read_timeout=15,
            retries={"max_attempts": 2},
            # Newer boto3 adds checksums that S3-compatible services may reject.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def save_locally(key, content):
    path = LOCAL_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def save_artifact(run_id, filename, content):
    """Upload one file, or save it locally if the upload fails for any reason."""
    key = f"reports/{run_id}/{filename}"
    bucket = os.getenv("S3_BUCKET", "estatemind-reports")

    try:
        create_s3_client().put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
        return f"s3://{bucket}/{key}"
    except (BotoCoreError, ClientError) as error:
        logger.warning("Cloud upload failed, saving %s locally: %s", key, error)
        return save_locally(key, content)


def save_run(run_id, files):
    """Save a run's files. A storage problem must never fail the user's report."""
    locations = {}
    for filename, content in files.items():
        try:
            locations[filename] = save_artifact(run_id, filename, content)
        except OSError as error:
            logger.error("Could not save %s: %s", filename, error)
    return locations
