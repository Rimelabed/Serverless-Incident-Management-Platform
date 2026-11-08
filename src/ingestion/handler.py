
import json
import os
import boto3
import base64
import binascii
import logging

from datetime import datetime


# Logging configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# AWS SQS client
AWS_REGION = os.environ.get("AWS_REGION", "eu-north-1")

sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION
)

# Queue URL provided through Lambda environment variables
QUEUE_URL = os.environ.get("QUEUE_URL")


# Incident validation rules
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

    if not isinstance(incident["incident_id"], str):
        raise ValueError("incident_id must be a string.")

    if not incident["incident_id"].startswith("INC-"):
        raise ValueError("Invalid incident_id format.")

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


def parse_request_body(event):
    """Extract and decode the HTTP request body."""

    body = event.get("body")

    if body is None:
        raise ValueError("Request body is missing.")

    if event.get("isBase64Encoded", False):
        if not isinstance(body, str):
            raise ValueError("Invalid Base64 request body.")

        try:
            body = base64.b64decode(
                body,
                validate=True
            ).decode("utf-8")

        except (binascii.Error, UnicodeDecodeError):
            raise ValueError("Invalid Base64 request body.")

    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise ValueError("Request body contains invalid JSON.")

    return body


def lambda_handler(event, context):
    """Receive, validate and enqueue an incident."""

    try:
        # Check HTTP method
        http_method = (
            event.get("requestContext", {})
            .get("http", {})
            .get("method")
        )

        if http_method and http_method != "POST":
            return {
                "statusCode": 405,
                "body": json.dumps({
                    "error": "Method not allowed."
                }),
            }

        # Extract request data
        incident = parse_request_body(event)

        # Validate incident
        validate_incident(incident)

        # Check AWS configuration
        if not QUEUE_URL:
            raise RuntimeError(
                "QUEUE_URL environment variable is not configured."
            )

        # Send incident to Amazon SQS
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(incident),
        )

        logger.info(
            "Incident accepted: %s",
            incident["incident_id"],
        )

        # Return HTTP 202 Accepted
        return {
            "statusCode": 202,
            "body": json.dumps({
                "message": "Incident accepted.",
                "incident_id": incident["incident_id"],
                "message_id": response["MessageId"],
            }),
        }

    except ValueError as error:
        logger.warning(
            "Invalid incident request: %s",
            error,
        )

        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": str(error)
            }),
        }

    except Exception:
        logger.exception(
            "Unexpected error while processing incident"
        )

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error."
            }),
        }
