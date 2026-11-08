import argparse
import json
import random
import uuid
from datetime import datetime, timezone


SERVICES = [
    "payment-service",
    "authentication-service",
    "order-service",
]

SEVERITIES = [
    "low",
    "medium",
    "high",
    "critical",
]

INCIDENT_DESCRIPTIONS = {
    "payment-service": [
        "Payment processing failures",
        "High payment response time",
        "Payment gateway unavailable",
    ],
    "authentication-service": [
        "Authentication failures",
        "High login response time",
        "Authentication service unavailable",
    ],
    "order-service": [
        "Order creation failures",
        "Order processing delay",
        "Order service unavailable",
    ],
}


def generate_incident():
    service = random.choice(SERVICES)
    severity = random.choice(SEVERITIES)
    description = random.choice(INCIDENT_DESCRIPTIONS[service])

    incident = {
        "incident_id": f"INC-{uuid.uuid4().hex[:8].upper()}",
        "service": service,
        "severity": severity,
        "description": description,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return incident


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic incidents for the Serverless platform."
    )

    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of incidents to generate (1 to 100).",
    )

    args = parser.parse_args()

    if args.count < 1 or args.count > 100:
        parser.error("--count must be between 1 and 100.")

    for _ in range(args.count):
        incident = generate_incident()
        print(json.dumps(incident))


if __name__ == "__main__":
    main()
