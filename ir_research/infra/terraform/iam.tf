resource "aws_iam_policy" "research" {
  name = "ir-research-experiment-policy"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "bedrock:InvokeModel"
        ]

        Resource = [
          "arn:aws:bedrock:ap-northeast-1::foundation-model/cohere.embed-multilingual-v3"
        ]
      },
      {
        Effect = "Allow"

        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]

        Resource = [
          aws_s3_bucket.research.arn
        ]
      },
      {
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]

        Resource = [
          "${aws_s3_bucket.research.arn}/*"
        ]
      }
    ]
  })
}