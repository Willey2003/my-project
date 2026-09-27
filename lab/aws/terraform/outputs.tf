output "alb_url" {
  value = "http://${aws_lb.app.dns_name}"
}

output "github_role_arn" {
  value = try(aws_iam_role.github_deployer[0].arn, "")
}

output "vpc_id" {
  value = aws_vpc.main.id
}
