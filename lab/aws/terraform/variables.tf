variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "owner" {
  type    = string
  default = "gaganpreet"
}

variable "name" {
  type    = string
  default = "lab"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "container_image" {
  description = "Image for the ECS service, e.g. ghcr.io/<you>/lab-api:<sha> from the CI/CD lab"
  type        = string
  default     = "public.ecr.aws/nginx/nginx:stable-alpine"
}

variable "container_port" {
  type    = number
  default = 80
}

variable "private_tasks" {
  description = "true = tasks in private subnets behind a NAT gateway (~USD 1.1/day extra). false = public subnets, still only reachable via the ALB security group."
  type        = bool
  default     = false
}

variable "alarm_email" {
  description = "Email for CloudWatch alarm + budget notifications (confirm the SNS subscription mail)"
  type        = string
  default     = ""
}

variable "monthly_budget_usd" {
  type    = number
  default = 10
}

variable "github_repo" {
  description = "owner/repo allowed to assume the CI role via OIDC; empty = skip"
  type        = string
  default     = ""
}
