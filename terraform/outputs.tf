
output "ingestion_function_name" {
  description = "Name of the ingestion Lambda"
  value       = aws_lambda_function.ingestion.function_name
}

output "ingestion_function_url" {
  description = "IAM-authenticated URL of the ingestion Lambda"
  value       = aws_lambda_function_url.ingestion.function_url
}

output "processor_function_name" {
  description = "Name of the processor Lambda"
  value       = aws_lambda_function.processor.function_name
}

output "sqs_queue_url" {
  description = "URL of the main incident queue"
  value       = aws_sqs_queue.incidents.url
}

output "sqs_dlq_url" {
  description = "URL of the dead-letter queue"
  value       = aws_sqs_queue.incidents_dlq.url
}

output "dynamodb_table_name" {
  description = "Name of the incident history table"
  value       = aws_dynamodb_table.incidents.name
}

output "sns_topic_arn" {
  description = "ARN of the critical incident notification topic"
  value       = aws_sns_topic.critical_incidents.arn
}
