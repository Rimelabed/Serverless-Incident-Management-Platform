
# ==========================================
# Local naming convention
# ==========================================

locals {
  resource_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}


# ==========================================
# Amazon SQS - Dead Letter Queue
# ==========================================

resource "aws_sqs_queue" "incidents_dlq" {
  name                      = "${local.resource_prefix}-dlq"
  message_retention_seconds = 1209600

  tags = local.common_tags
}


# ==========================================
# Amazon SQS - Main incident queue
# ==========================================

resource "aws_sqs_queue" "incidents" {
  name                       = "${local.resource_prefix}-queue"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.incidents_dlq.arn
    maxReceiveCount     = 3
  })

  tags = local.common_tags
}


# ==========================================
# Amazon DynamoDB - Incident history
# ==========================================

resource "aws_dynamodb_table" "incidents" {
  name         = "${local.resource_prefix}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "incident_id"

  attribute {
    name = "incident_id"
    type = "S"
  }

  tags = local.common_tags
}


# ==========================================
# Amazon SNS - Critical incident notifications
# ==========================================

resource "aws_sns_topic" "critical_incidents" {
  name = "${local.resource_prefix}-critical-incidents"

  tags = local.common_tags
}


# ==========================================
# SNS Email Subscription
# ==========================================

resource "aws_sns_topic_subscription" "email" {
  count = var.notification_email == null ? 0 : 1

  topic_arn = aws_sns_topic.critical_incidents.arn
  protocol  = "email"
  endpoint  = var.notification_email
}
