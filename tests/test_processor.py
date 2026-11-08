
import json
import pytest

from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from src.processor import handler


# ==========================================
# Test data
# ==========================================

@pytest.fixture
def valid_incident():
    return {
        "incident_id": "INC-12345678",
        "service": "payment-service",
        "severity": "high",
        "description": "Payment processing failures",
        "timestamp": "2026-11-08T15:00:00+00:00",
    }


@pytest.fixture
def mock_table():
    return MagicMock()


# ==========================================
# Tests for process_incident()
# ==========================================

def test_process_normal_incident(valid_incident, mock_table):
    """A normal incident must be stored without sending a notification."""

    with patch.object(handler, "table", mock_table), \
         patch.object(handler.sns, "publish") as mock_publish:

        result = handler.process_incident(valid_incident)

    assert result is True

    mock_table.put_item.assert_called_once()

    mock_publish.assert_not_called()


def test_process_critical_incident(valid_incident, mock_table):
    """A critical incident must be stored and trigger an SNS notification."""

    valid_incident["severity"] = "critical"

    with patch.object(handler, "table", mock_table), \
         patch.object(handler, "SNS_TOPIC_ARN", "arn:aws:sns:eu-north-1:123456789012:incidents"), \
         patch.object(handler.sns, "publish") as mock_publish:

        result = handler.process_incident(valid_incident)

    assert result is True

    mock_table.put_item.assert_called_once()

    mock_publish.assert_called_once()

    notification = mock_publish.call_args.kwargs

    assert notification["Subject"] == "CRITICAL INCIDENT: INC-12345678"
    assert notification["TopicArn"].endswith(":incidents")


def test_duplicate_incident_is_ignored(valid_incident, mock_table):
    """A duplicate incident must not be stored or notified again."""

    mock_table.put_item.side_effect = ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "Incident already exists",
            }
        },
        "PutItem",
    )

    with patch.object(handler, "table", mock_table), \
         patch.object(handler.sns, "publish") as mock_publish:

        result = handler.process_incident(valid_incident)

    assert result is False

    mock_table.put_item.assert_called_once()

    mock_publish.assert_not_called()


def test_dynamodb_error_is_propagated(valid_incident, mock_table):
    """Unexpected DynamoDB errors must be propagated."""

    mock_table.put_item.side_effect = ClientError(
        {
            "Error": {
                "Code": "InternalServerError",
                "Message": "DynamoDB unavailable",
            }
        },
        "PutItem",
    )

    with patch.object(handler, "table", mock_table):

        with pytest.raises(ClientError):
            handler.process_incident(valid_incident)


def test_missing_table_configuration(valid_incident):
    """Processing must fail if the DynamoDB table is not configured."""

    with patch.object(handler, "table", None):

        with pytest.raises(RuntimeError, match="TABLE_NAME"):

            handler.process_incident(valid_incident)


def test_missing_sns_configuration_for_critical_incident(
    valid_incident,
    mock_table,
):
    """A critical incident must fail if the SNS topic is not configured."""

    valid_incident["severity"] = "critical"

    with patch.object(handler, "table", mock_table), \
         patch.object(handler, "SNS_TOPIC_ARN", None):

        with pytest.raises(RuntimeError, match="SNS_TOPIC_ARN"):

            handler.process_incident(valid_incident)

    mock_table.put_item.assert_not_called()


def test_invalid_incident_is_not_stored(valid_incident, mock_table):
    """An invalid incident must not be stored."""

    valid_incident["severity"] = "urgent"

    with patch.object(handler, "table", mock_table):

        with pytest.raises(ValueError):

            handler.process_incident(valid_incident)

    mock_table.put_item.assert_not_called()


# ==========================================
# Tests for lambda_handler()
# ==========================================

def test_lambda_handler_processes_sqs_messages(valid_incident):
    """The Lambda handler must process all valid SQS messages."""

    event = {
        "Records": [
            {
                "messageId": "msg-001",
                "body": json.dumps(valid_incident),
            },
            {
                "messageId": "msg-002",
                "body": json.dumps(valid_incident),
            },
        ]
    }

    with patch.object(handler, "process_incident") as mock_process:

        result = handler.lambda_handler(event, None)

    assert result == {"batchItemFailures": []}

    assert mock_process.call_count == 2


def test_lambda_handler_reports_failed_messages(valid_incident):
    """Only failed SQS messages must be returned for retry."""

    event = {
        "Records": [
            {
                "messageId": "msg-001",
                "body": json.dumps(valid_incident),
            },
            {
                "messageId": "msg-002",
                "body": json.dumps(valid_incident),
            },
        ]
    }

    def process_side_effect(incident):
        if incident["incident_id"] == "INC-12345678":
            raise RuntimeError("DynamoDB unavailable")

    with patch.object(
        handler,
        "process_incident",
        side_effect=process_side_effect,
    ):

        result = handler.lambda_handler(event, None)

    assert result == {
        "batchItemFailures": [
            {"itemIdentifier": "msg-001"},
            {"itemIdentifier": "msg-002"},
        ]
    }


def test_lambda_handler_handles_invalid_json():
    """An invalid JSON message must be reported as failed."""

    event = {
        "Records": [
            {
                "messageId": "msg-invalid",
                "body": "{invalid-json}",
            }
        ]
    }

    result = handler.lambda_handler(event, None)

    assert result == {
        "batchItemFailures": [
            {"itemIdentifier": "msg-invalid"}
        ]
    }
