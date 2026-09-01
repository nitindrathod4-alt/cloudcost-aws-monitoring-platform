# CloudCost backend

The production backend is designed for AWS managed services: API Gateway + Lambda, IAM roles, AWS SDK (boto3), Cost Explorer, Budgets, CloudWatch, CloudTrail, EC2, RDS, S3, DynamoDB, EventBridge and SNS.

No AWS access keys belong in source code. Runtime permissions must be granted through an IAM execution role.
