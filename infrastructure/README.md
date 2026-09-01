# AWS Infrastructure

Target deployment is AWS-only and Docker-free.

- S3: static frontend
- CloudFront: CDN and TLS edge delivery
- Route 53: DNS
- WAF: web protection
- API Gateway: HTTPS API
- Lambda: application APIs and scheduled jobs
- DynamoDB: application snapshots / preferences
- Cost Explorer + AWS Budgets: cost intelligence
- CloudWatch + CloudTrail: monitoring and audit
- EventBridge + SNS: automation and notifications
- IAM + KMS + Secrets Manager: identity and secrets

Keep expensive services disabled until deployment needs them.
