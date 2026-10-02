terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Week 35: move state to S3 once you are comfortable (bucket + native S3 locking):
  # backend "s3" {
  #   bucket       = "tfstate-<account-id>-ap-south-1"
  #   key          = "lab/terraform.tfstate"
  #   region       = "ap-south-1"
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "devops-lab"
      Owner     = var.owner
      ManagedBy = "terraform"
    }
  }
}
