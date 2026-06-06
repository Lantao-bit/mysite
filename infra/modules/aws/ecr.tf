# -----------------------------------------------------------------------------
# ECR Repository
# -----------------------------------------------------------------------------

# ECR is account-scoped, so only one target should create it.
# Other targets reference it via data source.

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

data "aws_ecr_repository" "main" {
  count = var.create_ecr ? 0 : 1

  name = var.ecr_repo_name
}

locals {
  ecr_repo_arn  = var.create_ecr ? aws_ecr_repository.main[0].arn : data.aws_ecr_repository.main[0].arn
  ecr_repo_url  = var.create_ecr ? aws_ecr_repository.main[0].repository_url : data.aws_ecr_repository.main[0].repository_url
  ecr_repo_name = var.create_ecr ? aws_ecr_repository.main[0].name : data.aws_ecr_repository.main[0].name
}

# -----------------------------------------------------------------------------
# ECR Lifecycle Policy (only when we own the repo)
# -----------------------------------------------------------------------------

resource "aws_ecr_lifecycle_policy" "main" {
  count = var.create_ecr ? 1 : 0

  repository = local.ecr_repo_name

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
