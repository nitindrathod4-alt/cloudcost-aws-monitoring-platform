# CloudCost — AWS Cloud Cost & Resource Monitoring Platform

AWS-only cloud cost, resource, monitoring, and security dashboard.

## UI

- Dark CloudCost dashboard inspired by the approved reference design
- 10 routes/pages: Dashboard, Cost Explorer, Cost by Service, Resources, Budgets & Alerts, Reports, Monitoring, Security, Settings, Login
- Responsive frontend with reusable components

## AWS Services

Route 53, CloudFront, S3, API Gateway, Lambda, IAM, Cost Explorer, AWS Budgets, EC2, RDS, DynamoDB, CloudWatch, CloudTrail, WAF, KMS, Secrets Manager, EventBridge, SNS, VPC, Systems Manager.

## Important

No Docker, Kubernetes, ECS, or ECR are used in this project.

## Local frontend preview

Open `frontend/index.html` in a browser.

## AWS deployment direction

1. Host the static frontend in S3.
2. Put CloudFront in front of the S3 origin.
3. Use Route 53 for the custom domain.
4. Protect public web traffic with AWS WAF.
5. Use API Gateway + Lambda for application APIs.
6. Use IAM roles and Secrets Manager instead of hardcoded credentials.
