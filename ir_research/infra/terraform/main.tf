resource "aws_s3_bucket" "research" {
  bucket = "ir-research-${data.aws_caller_identity.current.account_id}-ap-northeast-1"

  tags = {
    Project = "ir_research"
    Managed = "Terrraform"
  }
}

resource "aws_s3_bucket_public_access_block" "research" {
  bucket = aws_s3_bucket.research.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "research" {
  bucket = aws_s3_bucket.research.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}