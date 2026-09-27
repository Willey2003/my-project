# AWS lab (weeks 33-35) - costs real money when applied

What `terraform apply` creates: VPC (2 AZ, public + private subnets), ALB, ECS Fargate service (2 tasks),
CloudWatch log group + unhealthy-target alarm to SNS email, monthly budget alert, optional GitHub OIDC role.

Rough cost in ap-south-1 while running: ALB ~USD 0.6/day + 2 small Fargate tasks ~USD 0.5/day,
+ NAT ~USD 1.1/day if `private_tasks = true`. **Run `terraform destroy` at the end of every study session.**

```bash
aws configure sso            # or an IAM user with MFA - never use root keys
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform plan -out plan.tfplan && terraform apply plan.tfplan
curl "$(terraform output -raw alb_url)"
terraform destroy
```

Drills:
1. Change a tag in the console, run `terraform plan` - that is drift. Decide: re-apply or import.
2. Set `desired_count = 0` via CLI (`aws ecs update-service`) and watch the alarm email arrive.
3. Deploy a broken image tag - the deployment circuit breaker rolls back. Find the event in the ECS console.
4. Flip `private_tasks = true`, apply, and explain why the tasks now need the NAT gateway (image pull).
5. Add ACM + Route 53 + HTTPS listener (443) with redirect from 80 once you own a domain.
