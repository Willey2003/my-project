---
tags: [devops-prep, guide]
---
# Phase 11 - AWS for DevOps

**Plan weeks:** 33-35 · **Hours:** 36 · **Cert:** none required (AWS DevOps Engineer Professional is the natural optional next step) · **Lab:** `lab/aws/terraform/` (run `terraform destroy` after every session)

| Week | Focus | Deliverable |
|---|---|---|
| 33 | AWS mental model, accounts & guardrails, IAM least privilege, VPC design | IAM role/policy set + VPC diagram |
| 34 | EC2, ECS Fargate, ALB + ACM, service discovery | Fargate service behind an ALB |
| 35 | Terraform, drift, CloudWatch alarms/paging, cost tagging, interview prep | Stack reproduced from Terraform + alarm that pages |

## Mental model
Everything is an API call: authenticated (who are you - IAM principal), authorised (policy evaluation), regional (most services), and billed. The console is for looking; Terraform is for changing.

**Accounts as blast-radius boundaries:** AWS Organizations with separate accounts (sandbox, dev, prod, security/logging). Service Control Policies set the maximum permissions for an account. Never use the root user day to day; enable MFA on root and lock it away. Use IAM Identity Center (SSO) for humans, roles for workloads.

## IAM (week 33)
- Principals: users (avoid), roles (preferred - temporary credentials via STS), services.
- Policy evaluation: explicit Deny > explicit Allow > implicit deny. Identity policies, resource policies (S3 bucket policy), permission boundaries, SCPs and session policies all intersect.
- Least privilege workflow: start narrow, use IAM Access Analyzer to generate policies from CloudTrail activity, review with `aws iam simulate-principal-policy`.
- Trust policy (who may assume a role) vs permission policy (what the role can do). The GitHub OIDC role in `github_oidc.tf` is the example to study.

## VPC (week 33)
- CIDR per VPC (e.g. 10.20.0.0/16), subnets per AZ. "Public" subnet = route table has 0.0.0.0/0 -> Internet Gateway. "Private" = no IGW route; outbound via NAT gateway (costs money) or VPC endpoints (S3/DynamoDB gateway endpoints are free; interface endpoints cost).
- Security groups: stateful, allow-only, attached to ENIs, can reference other SGs (ALB SG -> task SG pattern in `ecs.tf`). NACLs: stateless, subnet-level, allow + deny, ordered rules.
- Draw it: VPC, 2 AZs, public + private subnets, IGW, NAT, route tables, ALB, tasks. This diagram is the week 33 deliverable.

## Compute and containers (week 34)
- EC2 basics: AMIs, instance types, user data, instance profiles (roles for EC2), IMDSv2 required, EBS vs instance store, Auto Scaling groups + launch templates.
- ECS: cluster -> service (desired count, deployment config, circuit breaker) -> task definition (containers, CPU/mem, roles). Execution role = pull image + write logs; task role = what your app may call. Fargate = no servers to manage; `awsvpc` networking gives each task an ENI.
- ALB: listeners -> rules -> target groups (type `ip` for Fargate), health checks, deregistration delay. ACM issues free public certs that renew automatically when DNS-validated via Route 53.
- Service discovery: Cloud Map / ECS Service Connect for service-to-service names.

## Terraform (week 35)
```bash
terraform init ; terraform fmt -recursive ; terraform validate
terraform plan -out plan.tfplan ; terraform apply plan.tfplan
terraform state list ; terraform state show aws_lb.app ; terraform import <addr> <id>
terraform destroy
```
- State is the source of truth for what Terraform manages; keep it remote (S3 with native locking via `use_lockfile`) and never commit it.
- Drift: someone changes something in the console; `terraform plan` shows it. Decide whether code or reality is right, then re-apply or update code.
- Modules for reuse, `for_each` over `count` for stable addressing, `default_tags` for cost allocation.

## Observability and cost (week 35)
- CloudWatch Logs (log groups with retention), metrics, alarms -> SNS -> email/pager. The lab alarm fires on unhealthy ALB targets.
- CloudTrail for API audit; AWS Config for resource compliance; GuardDuty for threat detection (know what each is for).
- Budgets + Cost Explorer; tag everything (`Project`, `Owner`, `Env`).

## Interview prep
Work through 75-aws-interview-questions-for-devops.pdf. Be ready to whiteboard: a three-tier app across 2 AZs, a zero-downtime ECS deploy, how you would give CI access to AWS without keys, and how you would cut a surprise bill.

## Self-check
1. Why can't Fargate tasks in private subnets pull a public image without extra setup?
2. Security group vs NACL?
3. Execution role vs task role?
4. What happens on `terraform apply` after someone deleted a resource in the console?
5. How do you stop a sandbox account from ever launching resources outside ap-south-1?

<details><summary>Answers</summary>

1. No route to the internet: add a NAT gateway or VPC endpoints (ECR, S3, Logs).
2. SG stateful, instance/ENI level, allow-only; NACL stateless, subnet level, allow and deny.
3. Execution role is used by ECS to pull images and send logs; task role is assumed by your application code.
4. Terraform sees it missing from reality and recreates it.
5. An SCP denying actions when `aws:RequestedRegion` is not ap-south-1 (with exceptions for global services).
</details>

## Resources
aws-for-devops.pdf (12 ch.), 75-aws-interview-questions-for-devops.pdf, https://docs.aws.amazon.com, https://aws.amazon.com/free, https://developer.hashicorp.com/terraform/tutorials/aws-get-started


---
[[Home]] · [[Schedule]]
