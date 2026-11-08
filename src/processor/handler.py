
import json
import os
import boto3
import logging

from datetime import datetime, timezone
from botocore.exceptions import ClientError


# ==========================================
# Logging configuration
# ==========================================

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ==========================================
# AWS configuration
# ==========================================

AWS_REGION = os.environ.get("AWS_REGION", "eu-north-1")

TABLE_NAME = os.environ.get("TABLE_NAME")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")


# ==========================================
# AWS clients and resources
# ==========================================

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)

sns = boto3.client(
    "sns",
    region_name=AWS_REGION
)

table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None


# ==========================================
# Incident validation rules
# ==========================================

REQUIRED_FIELDS = {
    "incident_id",
    "service",
    "severity",
    "description",
    "timestamp",
}

VALID_SERVICES = {
    "payment-service",
    "authentication-service",
    "order-service",
}

VALID_SEVERITIES = {
    "low",
    "medium",
    "high",
    "critical",
}


def validate_incident(incident):
    """Validate the structure and values of an incident."""

    if not isinstance(incident, dict):
        raise ValueError("Incident must be a JSON object.")

    missing_fields = REQUIRED_FIELDS - set(incident.keys())

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {', '.join(sorted(missing_fields))}"
        )

    if (
        not isinstance(incident["incident_id"], str)
        or not incident["incident_id"].startswith("INC-")
    ):
        raise ValueError("Invalid incident_id.")

    if incident["service"] not in VALID_SERVICES:
        raise ValueError("Invalid service.")

    if incident["severity"] not in VALID_SEVERITIES:
        raise ValueError("Invalid severity.")

    if (
        not isinstance(incident["description"], str)
        or not incident["description"].strip()
    ):
        raise ValueError("Description must be a non-empty string.")

    if not isinstance(incident["timestamp"], str):
        raise ValueError("Timestamp must be a string.")

    try:
        timestamp = datetime.fromisoformat(
            incident["timestamp"].replace("Z", "+00:00")
        )
    except ValueError:
        raise ValueError("Invalid timestamp format.")

    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")

    return True


# ==========================================
# Process one incident
# ==========================================

def process_incident(incident):
    """Store an incident and notify if it is critical."""

    if table is None:
        raise RuntimeError("TABLE_NAME is not configured.")

    validate_incident(incident)

    # Check SNS configuration before processing critical incidents
    if incident["severity"] == "critical" and not SNS_TOPIC_ARN:
        raise RuntimeError("SNS_TOPIC_ARN is not configured.")

    incident_id = incident["incident_id"]

    item = {
        **incident,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Conditional write ensures that an incident is stored only once
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(incident_id)",
        )

        logger.info(
            "Incident stored successfully: %s",
            incident_id,
        )

    except ClientError as error:

        error_code = error.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            logger.info(
                "Duplicate incident ignored: %s",
                incident_id,
            )

            return False

        raise

    # Send notification only for critical incidents
    if incident["severity"] == "critical":

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"CRITICAL INCIDENT: {incident_id}",
            Message=json.dumps(item),
        )

        logger.info(
            "Critical incident notification sent: %s",
            incident_id,
        )

    return True


# ==========================================
# Lambda handler triggered by SQS
# ==========================================

def lambda_handler(event, context):
    """Process incidents received from an SQS event."""

    batch_item_failures = []

    records = event.get("Records", [])

    for record in records:

        message_id = record.get("messageId")

        try:
            # Extract incident from SQS message body
            body = json.loads(record["body"])

            # Process the incident
            process_incident(body)

        except Exception:

            logger.exception(
                "Failed to process SQS message: %s",
                message_id,
            )

            # Tell SQS to retry only this failed message
            if message_id:
                batch_item_failures.append({
                    "itemIdentifier": message_id
                })

    logger.info(
        "Batch processing completed. Failed messages: %d",
        len(batch_item_failures),
    )

    return {
        "batchItemFailures": batch_item_failures
    }
