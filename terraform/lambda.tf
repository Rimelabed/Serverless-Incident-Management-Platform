
# ==========================================
# Package Lambda - Ingestion
# ==========================================

data "archive_file" "ingestion" {
  type        = "zip"
  source_file = "${path.module}/../src/ingestion/handler.py"
  output_path = "${path.module}/build/ingestion.zip"
}


# ==========================================
# Package Lambda - Processor
# ==========================================

data "archive_file" "processor" {
  type        = "zip"
  source_file = "${path.module}/../src/processor/handler.py"
  output_path = "${path.module}/build/processor.zip"
}


# ==========================================
# CloudWatch Log Groups
# ==========================================

resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${local.resource_prefix}-ingestion"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "processor" {
  name              = "/aws/lambda/${local.resource_prefix}-processor"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}


# ==========================================
# Lambda 1 - Incident Ingestion
# ==========================================

resource "aws_lambda_function" "ingestion" {
  function_name = "${local.resource_prefix}-ingestion"
  description   = "Receives and validates incidents before sending them to SQS."

  role    = aws_iam_role.ingestion_lambda.arn
  runtime = var.lambda_runtime
  handler = "handler.lambda_handler"

  filename         = data.archive_file.ingestion.output_path
  source_code_hash = data.archive_file.ingestion.output_base64sha256

  timeout     = 10
  memory_size = 128

  environment {
    variables = {
      QUEUE_URL = aws_sqs_queue.incidents.url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.ingestion_logs,
    aws_iam_role_policy.ingestion_sqs,
    aws_cloudwatch_log_group.ingestion
  ]

  tags = local.common_tags
}


# ==========================================
# Lambda Function URL
# ==========================================

resource "aws_lambda_function_url" "ingestion" {
  function_name      = aws_lambda_function.ingestion.function_name
  authorization_type = "AWS_IAM"
}


# Allow IAM-authenticated Function URL invocation

resource "aws_lambda_permission" "ingestion_url" {
  statement_id           = "AllowFunctionURLInvocation"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.ingestion.function_name
  principal              = "*"
  function_url_auth_type = "AWS_IAM"
}

resource "aws_lambda_permission" "ingestion_url_invoke" {
  statement_id             = "AllowFunctionURLInvokeFunction"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.ingestion.function_name
  principal                = "*"
  invoked_via_function_url = true
}


# ==========================================
# Lambda 2 - Incident Processor
# ==========================================

resource "aws_lambda_function" "processor" {
  function_name = "${local.resource_prefix}-processor"
  description   = "Processes incidents received from SQS."

  role    = aws_iam_role.processor_lambda.arn
  runtime = var.lambda_runtime
  handler = "handler.lambda_handler"

  filename         = data.archive_file.processor.output_path
  source_code_hash = data.archive_file.processor.output_base64sha256

  timeout     = 10
  memory_size = 128

  environment {
    variables = {
      TABLE_NAME    = aws_dynamodb_table.incidents.name
      SNS_TOPIC_ARN = aws_sns_topic.critical_incidents.arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.processor_logs,
    aws_iam_role_policy.processor_sqs,
    aws_iam_role_policy.processor_dynamodb,
    aws_iam_role_policy.processor_sns,
    aws_cloudwatch_log_group.processor
  ]

  tags = local.common_tags
}


# ==========================================
# SQS Event Source Mapping
# ==========================================

resource "aws_lambda_event_source_mapping" "processor_sqs" {
  event_source_arn = aws_sqs_queue.incidents.arn
  function_name    = aws_lambda_function.processor.arn

  batch_size              = 5
  function_response_types = ["ReportBatchItemFailures"]
  enabled                 = true
}
