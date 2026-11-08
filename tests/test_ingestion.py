import json
from unittest.mock import patch

from src.ingestion import handler


def test_valid_incident_is_sent_to_sqs():
    incident = {
        "incident_id": "INC-12345678",
        "service": "payment-service",
        "severity": "high",
        "description": "Payment processing failures",
        "timestamp": "2026-11-08T15:57:01+00:00",
    }

    event = {
        "requestContext": {
            "http": {
                "method": "POST"
            }
        },
        "body": json.dumps(incident),
        "isBase64Encoded": False,
    }

    with patch.object(handler, "QUEUE_URL", "https://fake-sqs-url"):

        with patch.object(handler.sqs, "send_message") as mock_send:

            mock_send.return_value = {
                "MessageId": "mock-message-123"
            }

            response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 202

    mock_send.assert_called_once()

    sent_message = mock_send.call_args.kwargs

    assert sent_message["QueueUrl"] == "https://fake-sqs-url"
    assert json.loads(sent_message["MessageBody"]) == incident

def test_invalid_severity_returns_400():
    incident = {
        "incident_id": "INC-12345678",
        "service": "payment-service",
        "severity": "urgent",
        "description": "Payment processing failures",
        "timestamp": "2026-11-08T15:57:01+00:00",
    }

    event = {
        "requestContext": {
            "http": {
                "method": "POST"
            }
        },
        "body": json.dumps(incident),
        "isBase64Encoded": False,
    }

    with patch.object(handler, "QUEUE_URL", "https://fake-sqs-url"):
        response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 400

def test_missing_required_field_returns_400():
    incident = {
        "incident_id": "INC-12345678",
        "service": "payment-service",
        "severity": "high",
        "timestamp": "2026-11-08T15:57:01+00:00",
    }

    event = {
        "requestContext": {
            "http": {
                "method": "POST"
            }
        },
        "body": json.dumps(incident),
        "isBase64Encoded": False,
    }

    with patch.object(handler, "QUEUE_URL", "https://fake-sqs-url"):
        with patch.object(handler.sqs, "send_message") as mock_send:
            response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 400
    mock_send.assert_not_called()

def test_invalid_json_returns_400():
    event = {
        "requestContext": {
            "http": {
                "method": "POST"
            }
        },
        "body": '{"incident_id": "INC-123", "severity":',
        "isBase64Encoded": False,
    }

    with patch.object(handler, "QUEUE_URL", "https://fake-sqs-url"):
        with patch.object(handler.sqs, "send_message") as mock_send:
            response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 400
    mock_send.assert_not_called()

def test_get_method_returns_405():
    event = {
        "requestContext": {
            "http": {
                "method": "GET"
            }
        },
        "body": "{}",
        "isBase64Encoded": False,
    }

    response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 405

def test_missing_body_returns_400():
    event = {
        "requestContext": {
            "http": {"method": "POST"}
        },
        "body": None,
        "isBase64Encoded": False,
    }

    response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 400

def test_missing_queue_url_returns_500():
    incident = {
        "incident_id": "INC-12345678",
        "service": "payment-service",
        "severity": "high",
        "description": "Payment processing failures",
        "timestamp": "2026-11-08T15:57:01+00:00",
    }

    event = {
        "requestContext": {
            "http": {"method": "POST"}
        },
        "body": json.dumps(incident),
        "isBase64Encoded": False,
    }

    with patch.object(handler, "QUEUE_URL", None):
        with patch.object(handler.sqs, "send_message") as mock_send:
            response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 500
    mock_send.assert_not_called()

def test_sqs_failure_returns_500():
    incident = {
        "incident_id": "INC-12345678",
        "service": "payment-service",
        "severity": "high",
        "description": "Payment processing failures",
        "timestamp": "2026-11-08T15:57:01+00:00",
    }

    event = {
        "requestContext": {
            "http": {"method": "POST"}
        },
        "body": json.dumps(incident),
        "isBase64Encoded": False,
    }

    with patch.object(handler, "QUEUE_URL", "https://fake-sqs-url"):
        with patch.object(handler.sqs, "send_message") as mock_send:
            mock_send.side_effect = Exception("SQS unavailable")

            response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 500