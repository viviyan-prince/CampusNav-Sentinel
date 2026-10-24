# CampusNav Sentinel — AWS Deployment

## Current Status: Deployment-Ready, Not Deployed

AWS CLI was not installed on the development machine. All deployment infrastructure files are prepared and documented but have not been executed against a live AWS account.

**The application runs fully without AWS.** AWS integration is optional and controlled by the `CN_AWS_ENABLED=true` environment variable.

## Prepared Infrastructure

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage container build |
| `deploy/docker-compose.yml` | Local container orchestration |
| `deploy/aws-cloudformation.yml` | ECS Fargate + ALB + S3 + CloudWatch stack |
| `deploy/deploy.sh` | Build, push, and deploy automation script |
| `.env.example` | Environment variable configuration template |

## Architecture

```
User Browser
    │
    ▼
Application Load Balancer (HTTPS, port 80)
    │
    ▼
ECS Fargate Service
├── FastAPI Application (port 8000)
├── YOLOv8n Model (loaded at startup)
└── OpenCV 5 Processing
    │
    ├──▶ S3 Bucket
    │    ├── uploads/    (input videos)
    │    └── outputs/    (annotated videos + reports)
    │
    └──▶ CloudWatch
         ├── Application logs
         └── Custom metrics (FPS, detections, hazard scores)
```

## Deployment Steps (When AWS Access is Available)

### Prerequisites
- AWS CLI v2 installed and configured
- AWS account with permissions for ECS, ECR, S3, CloudWatch, ALB, VPC
- Docker installed

### Step 1: Configure and Deploy
```bash
# 1. Install AWS CLI and configure credentials
aws configure

# 2. Set required environment variables
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 3. Dry run first
DRY_RUN=true bash deploy/deploy.sh

# 4. Deploy for real
bash deploy/deploy.sh
```

### Step 2: Verify
```bash
# Get the ALB URL from stack outputs
aws cloudformation describe-stacks --stack-name campusnav-sentinel \
  --query 'Stacks[0].Outputs[?OutputKey==`ServiceUrl`].OutputValue' --output text

# Health check
curl http://<ALB_URL>/health
```

## Estimated Costs

| Service | Estimated Monthly Cost | Notes |
|---|---|---|
| ECS Fargate (0.25 vCPU, 0.5 GB) | ~$9 | CPU-only; GPU instances cost more |
| ALB | ~$16 | Minimum hourly charge |
| S3 (< 1 GB) | < $1 | Depends on video storage volume |
| CloudWatch | < $1 | Logs and basic metrics |
| ECR | < $1 | Container image storage |
| **Total (demo)** | **~$27/month** | |

For competition demo purposes, a CPU-only Fargate task is sufficient with slower inference.

## Cleanup

```bash
# Delete the CloudFormation stack (removes all AWS resources)
aws cloudformation delete-stack --stack-name campusnav-sentinel

# Delete ECR repository
aws ecr delete-repository --repository-name campusnav-sentinel --force

# Verify deletion
aws cloudformation wait stack-delete-complete --stack-name campusnav-sentinel
```

## Environment Variables for AWS

| Variable | Default | Description |
|---|---|---|
| `CN_AWS_ENABLED` | `false` | Enable AWS integration |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region |
| `CN_S3_BUCKET` | (empty) | S3 bucket name for artifacts |

## Why AWS Integration Matters

Even without live deployment, the architecture demonstrates:
1. **Containerization** — Application packaged for reproducible deployment
2. **Cloud-native design** — Stateless API with external storage (S3)
3. **Observability** — CloudWatch integration for production monitoring
4. **Infrastructure as Code** — CloudFormation for repeatable deployments
5. **Isolation** — AWS features behind a feature flag; local-first design
