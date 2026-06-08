# -----------------------------------------------------------------------------
# ECR Repository
# -----------------------------------------------------------------------------

# ECR is account-scoped, so only one target should create it.
# Other targets construct the ARN/URL from the known repo name (no API call).

data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "main" {
  count = var.create_ecr ? 1 : 0

  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-ecr"
  }
}

locals {
  account_id   = data.aws_caller_identity.current.account_id
  ecr_repo_arn = var.create_ecr ? aws_ecr_repository.main[0].arn : "arn:aws:ecr:${var.region}:${local.account_id}:repository/${var.ecr_repo_name}"
  ecr_repo_url = var.create_ecr ? aws_ecr_repository.main[0].repository_url : "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_repo_name}"
}

# -----------------------------------------------------------------------------
# ECR Lifecycle Policy (only when we own the repo)
# -----------------------------------------------------------------------------

resource "aws_ecr_lifecycle_policy" "main" {
  count = var.create_ecr ? 1 : 0

  repository = aws_ecr_repository.main[0].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "latest"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# IAM Policy for EKS Nodes to Pull from ECR
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "ecr_pull" {
  name = "${var.cluster_name}-ecr-pull"
  role = aws_iam_role.eks_nodes.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetAuthorizationToken",
        ]
        Resource = [
          local.ecr_repo_arn,
          "${local.ecr_repo_arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Resource = "*"
      }
    ]
  })
}
