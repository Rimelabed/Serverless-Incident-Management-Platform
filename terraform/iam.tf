
# ==========================================
# IAM Role - Ingestion Lambda
# ==========================================

resource "aws_iam_role" "ingestion_lambda" {
  name = "${local.resource_prefix}-ingestion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}


# CloudWatch Logs permissions

resource "aws_iam_role_policy_attachment" "ingestion_logs" {
  role = aws_iam_role.ingestion_lambda.name

  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


# SQS SendMessage permission

resource "aws_iam_role_policy" "ingestion_sqs" {
  name = "${local.resource_prefix}-ingestion-sqs-policy"
  role = aws_iam_role.ingestion_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:SendMessage"
      ]
      Resource = aws_sqs_queue.incidents.arn
    }]
  })
}


# ==========================================
# IAM Role - Processor Lambda
# ==========================================

resource "aws_iam_role" "processor_lambda" {
  name = "${local.resource_prefix}-processor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}


# CloudWatch Logs permissions

resource "aws_iam_role_policy_attachment" "processor_logs" {
  role = aws_iam_role.processor_lambda.name

  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


# SQS permissions

resource "aws_iam_role_policy" "processor_sqs" {
  name = "${local.resource_prefix}-processor-sqs-policy"
  role = aws_iam_role.processor_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ]
      Resource = aws_sqs_queue.incidents.arn
    }]
  })
}


# DynamoDB permissions

resource "aws_iam_role_policy" "processor_dynamodb" {
  name = "${local.resource_prefix}-processor-dynamodb-policy"
  role = aws_iam_role.processor_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem"
      ]
      Resource = aws_dynamodb_table.incidents.arn
    }]
  })
}


# SNS permissions

resource "aws_iam_role_policy" "processor_sns" {
  name = "${local.resource_prefix}-processor-sns-policy"
  role = aws_iam_role.processor_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sns:Publish"
      ]
      Resource = aws_sns_topic.critical_incidents.arn
    }]
  })
}
