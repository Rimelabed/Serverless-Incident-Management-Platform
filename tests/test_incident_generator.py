from datetime import datetime
from simulator.incident_generator import (
    generate_incident,
    SERVICES,
    SEVERITIES,
)


def test_incident_has_required_fields():
    incident = generate_incident()

    expected_fields = {
        "incident_id",
        "service",
        "severity",
        "description",
        "timestamp",
    }

    assert set(incident.keys()) == expected_fields


def test_incident_id_is_valid():
    incident = generate_incident()

    assert incident["incident_id"].startswith("INC-")
    assert len(incident["incident_id"]) == 12


def test_service_is_valid():
    incident = generate_incident()

    assert incident["service"] in SERVICES


def test_severity_is_valid():
    incident = generate_incident()

    assert incident["severity"] in SEVERITIES


def test_timestamp_is_valid():
    incident = generate_incident()

    timestamp = datetime.fromisoformat(incident["timestamp"])

    assert timestamp.tzinfo is not None
