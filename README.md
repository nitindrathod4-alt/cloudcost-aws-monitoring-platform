# CloudCost — AWS Cloud Cost & Resource Monitoring Platform

A professional AWS-only cloud cost, resource, monitoring, security, and alerting dashboard.

![CloudCost](https://img.shields.io/badge/AWS-Only-orange)
![Frontend](https://img.shields.io/badge/UI-Dark%20Dashboard-1f6feb)
![Architecture](https://img.shields.io/badge/Architecture-Serverless-8b5cf6)

## What this project is

CloudCost provides one dashboard for AWS spend and infrastructure visibility while keeping the approved dark CloudCost UI unchanged.

### 10 pages

1. Dashboard
2. Cost Explorer
3. Cost by Service
4. Resources
5. Budgets & Alerts
6. Reports
7. Monitoring
8. Security
9. Settings
10. Login / Auth

## AWS-only architecture

```text
User
  |
Route 53 (optional custom domain)
  |
CloudFront + AWS WAF
  |
Private S3 frontend
  |
API Gateway
  |
Lambda + Boto3
  |
  +-- Cost Explorer / AWS Budgets
  +-- EC2 / RDS / S3 / Lambda / CloudFront
  +-- CloudWatch / CloudTrail / IAM / WAF
  +-- DynamoDB snapshots
  +-- SNS alerts
        ^
        |
  EventBridge scheduled refresh
```

## AWS services

- Route 53
- CloudFront
- S3
- WAF
- API Gateway
- Lambda
- Cost Explorer
- AWS Budgets
- EC2
- RDS
- DynamoDB
- CloudWatch
- CloudTrail
- IAM
- KMS-ready S3/DynamoDB encryption
- Secrets Manager-ready application design
- EventBridge
- SNS
- VPC/Security Groups where application-side resources require them
- Systems Manager for optional EC2 administration

## Explicitly not used

- Docker
- Docker Compose
- Kubernetes
- ECS
- ECR

## Repository structure

```text
cloudcost-aws-monitoring-platform/
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
│       ├── app.js
│       ├── config.js
│       └── aws-live.js
├── backend/
│   ├── lambda_handler.py
│   └── requirements.txt
├── infrastructure/
│   ├── template.yaml
│   └── DEPLOYMENT.md
├── .env.example
└── README.md
```

## Live AWS data

Set the API Gateway endpoint in `frontend/js/config.js`:

```javascript
window.CLOUDCOST_CONFIG = Object.freeze({
  API_BASE_URL: "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod"
});
```

The browser never receives AWS access keys. Lambda uses its IAM execution role to call AWS services.

## Deploy

Read the complete step-by-step guide:

`infrastructure/DEPLOYMENT.md`

Core deployment:

```bash
sam build -t infrastructure/template.yaml
sam deploy --guided --template-file .aws-sam/build/template.yaml
aws s3 sync frontend/ s3://YOUR_FRONTEND_BUCKET/ --delete
```

## Important AWS cost note

Cost Explorer is a billing API and AWS charges can take time to appear or update. Cost Explorer queries are made against the AWS billing service endpoint rather than the application Region.

## Security principles

- No AWS credentials in frontend JavaScript
- IAM role for Lambda
- Private S3 bucket behind CloudFront Origin Access Control
- HTTPS through CloudFront
- AWS WAF managed common rule set
- DynamoDB server-side encryption
- Least-privilege read access for monitored AWS services
- SNS used only by the scheduled backend alert path

## License

MIT
