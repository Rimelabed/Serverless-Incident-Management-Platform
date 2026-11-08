
variable "aws_region" {
  description = "AWS region where resources will be deployed"
  type        = string
  default     = "eu-north-1"
}

variable "project_name" {
  description = "Name of the Serverless Incident Management project"
  type        = string
  default     = "serverless-incident-management"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "lambda_runtime" {
  description = "Python runtime used by Lambda functions"
  type        = string
  default     = "python3.13"
}

variable "log_retention_days" {
  description = "CloudWatch logs retention period"
  type        = number
  default     = 7
}
variable "notification_email" {
  description = "Email address receiving critical incident notifications"
  type        = string
  default     = null
  nullable    = true
}