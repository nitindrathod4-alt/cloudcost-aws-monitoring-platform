# CloudCost AWS Deployment Guide

CloudCost is AWS-only. It does not use Docker, Kubernetes, ECS, or ECR.

## AWS architecture

```text
Route 53 (custom domain, optional)
        |
CloudFront + AWS WAF
        |
S3 static frontend
        |
Browser ---> API Gateway ---> Lambda (Python/Boto3)
                              |
        +---------------------+----------------------+
        |                     |                      |
 Cost Explorer             Budgets              Resources
        |                     |                      |
 EC2 / RDS / S3 / Lambda / CloudFront / CloudWatch / CloudTrail / IAM / WAF
                              |
                       DynamoDB snapshots
                              |
                         SNS alerts
                              ^
                              |
                     EventBridge every 6h
```

AWS Lambda Python runtimes include the AWS SDK for Python (Boto3), and Lambda uses the execution role credentials when calling AWS services. CloudCost therefore does not put AWS access keys in frontend code or source files.

## 1. Prerequisites

Install and configure:

- AWS CLI
- AWS SAM CLI
- Git

Authenticate with an AWS profile that has permission to create the resources in `infrastructure/template.yaml`.

```bash
aws configure
aws sts get-caller-identity
sam --version
```

## 2. Deploy the AWS backend

From the repository root:

```bash
sam build -t infrastructure/template.yaml
sam deploy --guided --template-file .aws-sam/build/template.yaml
```

Recommended guided values:

```text
Stack Name: cloudcost
AWS Region: ap-south-1
ProjectName: cloudcost
AppRegion: ap-south-1
CORSOrigin: *
Confirm changes before deploy: Y
Allow SAM CLI IAM role creation: Y
Disable rollback: N
```

The stack creates:

- API Gateway
- Lambda
- IAM permissions for read-only AWS monitoring APIs plus DynamoDB/SNS writes
- DynamoDB snapshot table
- SNS alert topic
- EventBridge scheduled refresh
- S3 frontend bucket
- CloudFront distribution
- CloudFront Origin Access Control
- AWS WAF managed common rule set

## 3. Get the API URL

```bash
aws cloudformation describe-stacks \
  --stack-name cloudcost \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text
```

Copy the returned API Gateway URL.

## 4. Configure the frontend

Edit:

```text
frontend/js/config.js
```

Set:

```javascript
API_BASE_URL: "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod"
```

Do not put AWS access keys, secret keys, session tokens, or database passwords in this file.

## 5. Upload the frontend to S3

Get the bucket name:

```bash
aws cloudformation describe-stacks \
  --stack-name cloudcost \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucket'].OutputValue" \
  --output text
```

Then upload:

```bash
aws s3 sync frontend/ s3://YOUR_FRONTEND_BUCKET/ --delete
```

## 6. Open CloudFront

Get the CloudFront domain:

```bash
aws cloudformation describe-stacks \
  --stack-name cloudcost \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomain'].OutputValue" \
  --output text
```

Open the returned `https://...cloudfront.net` address.

The S3 bucket remains private; CloudFront reads it through Origin Access Control.

## 7. Route 53 custom domain

If you own a domain:

1. Create or use a Route 53 hosted zone.
2. Request an ACM certificate in `us-east-1` for the CloudFront hostname you want, for example `cloudcost.example.com`.
3. Validate the certificate.
4. Add the certificate and alternate domain name to the CloudFront distribution.
5. Create a Route 53 alias A/AAAA record pointing the domain to CloudFront.

The domain can then be used as the public CloudCost URL.

## 8. SNS email alerts

Get the SNS topic ARN:

```bash
aws cloudformation describe-stacks \
  --stack-name cloudcost \
  --query "Stacks[0].Outputs[?OutputKey=='AlertTopicArn'].OutputValue" \
  --output text
```

Create an email subscription:

```bash
aws sns subscribe \
  --topic-arn YOUR_ALERT_TOPIC_ARN \
  --protocol email \
  --notification-endpoint YOUR_EMAIL@example.com
```

Confirm the subscription from the email.

The scheduled Lambda refresh publishes a budget alert when the configured AWS budget reaches 80% or more.

## 9. AWS permissions used by Lambda

The Lambda role is intentionally limited to the APIs needed by the dashboard:

- Cost Explorer: cost and forecast reads
- Budgets: budget reads
- EC2: instance discovery
- RDS: database discovery
- S3: bucket discovery
- Lambda: function discovery
- CloudFront: distribution discovery
- CloudWatch: metric reads
- CloudTrail: trail status reads
- IAM: account summary reads
- WAF: CloudFront Web ACL discovery
- STS: account identity
- DynamoDB: snapshot writes
- SNS: alert publishing

## 10. Cost Explorer note

Cost Explorer queries are made through the AWS Cost Explorer API. The API supports time periods, daily/monthly granularity, metrics, and grouping such as `SERVICE`.

Cost data can take time to become available in a newly created AWS account, so an empty or delayed cost response is possible even when the Lambda permissions are correct.

## 11. Local frontend preview

You can preview the UI without AWS data by opening:

```text
frontend/index.html
```

If `API_BASE_URL` is empty, the reference-style preview values remain visible. Once the API URL is configured, the same UI starts replacing the preview values with AWS data.

## 12. Verify APIs

```bash
curl https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/api/dashboard
curl https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/api/resources
curl https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/api/monitoring
curl https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/api/security
curl https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/api/budgets
```

## 13. CloudWatch logs

Lambda logs are automatically available in CloudWatch Logs. Check them when an AWS service permission or API call fails.

```bash
sam logs -n CloudCostFunction --stack-name cloudcost --tail
```

## 14. Update the application

After code changes:

```bash
sam build -t infrastructure/template.yaml
sam deploy --stack-name cloudcost --template-file .aws-sam/build/template.yaml
aws s3 sync frontend/ s3://YOUR_FRONTEND_BUCKET/ --delete
```

If CloudFront cache delays a frontend change, create an invalidation:

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

## 15. Cleanup

When finished with the project:

```bash
aws cloudformation delete-stack --stack-name cloudcost
```

If the frontend bucket contains objects, empty it first:

```bash
aws s3 rm s3://YOUR_FRONTEND_BUCKET --recursive
aws cloudformation delete-stack --stack-name cloudcost
```
