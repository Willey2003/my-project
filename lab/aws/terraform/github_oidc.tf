# Week 21/35: let GitHub Actions deploy with short-lived credentials (no access keys).
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.github_repo == "" ? 0 : 1
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_assume" {
  count = var.github_repo == "" ? 0 : 1
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_deployer" {
  count              = var.github_repo == "" ? 0 : 1
  name               = "${var.name}-github-deployer"
  assume_role_policy = data.aws_iam_policy_document.github_assume[0].json
}

# Least privilege: only roll the ECS service to a new task definition.
data "aws_iam_policy_document" "deployer" {
  statement {
    actions   = ["ecs:UpdateService", "ecs:DescribeServices"]
    resources = [aws_ecs_service.app.id]
  }
  statement {
    actions   = ["ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition"]
    resources = ["*"]
  }
  statement {
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.execution.arn]
  }
}

resource "aws_iam_role_policy" "deployer" {
  count  = var.github_repo == "" ? 0 : 1
  role   = aws_iam_role.github_deployer[0].id
  policy = data.aws_iam_policy_document.deployer.json
}
