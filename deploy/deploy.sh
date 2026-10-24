#!/usr/bin/env bash
set -euo pipefail

# CampusNav Sentinel — AWS Deployment Script
#
# Usage:
#   ./deploy/deploy.sh                  # Full deploy
#   DRY_RUN=1 ./deploy/deploy.sh        # Print commands without executing
#   ./deploy/deploy.sh teardown          # Delete stack and ECR repo
#
# Required env vars:
#   AWS_ACCOUNT_ID    — AWS account number
#   AWS_REGION        — Target region (default: us-east-1)
#   VPC_ID            — VPC for deployment
#   SUBNET_IDS        — Comma-separated public subnet IDs
#
# AWS CLI and Docker must be installed and authenticated.

STACK_NAME="${STACK_NAME:-campusnav-sentinel}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="${ECR_REPO:-campusnav-sentinel}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DRY_RUN="${DRY_RUN:-0}"

run() {
    echo "+ $*"
    if [ "$DRY_RUN" = "1" ]; then
        echo "  [DRY RUN — skipped]"
    else
        "$@"
    fi
}

check_prereqs() {
    for cmd in aws docker; do
        if ! command -v "$cmd" &>/dev/null; then
            echo "ERROR: $cmd is required but not found."
            exit 1
        fi
    done

    if [ -z "${AWS_ACCOUNT_ID:-}" ]; then
        echo "ERROR: AWS_ACCOUNT_ID is not set."
        exit 1
    fi
}

ECR_URI="${AWS_ACCOUNT_ID:-000000000000}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

build_and_push() {
    echo "=== Building Docker image ==="
    run docker build -t "${ECR_REPO}:${IMAGE_TAG}" -f Dockerfile .

    echo "=== Creating ECR repository (if needed) ==="
    run aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${AWS_REGION}" 2>/dev/null \
        || run aws ecr create-repository --repository-name "${ECR_REPO}" --region "${AWS_REGION}"

    echo "=== Authenticating Docker to ECR ==="
    if [ "$DRY_RUN" != "1" ]; then
        aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    else
        echo "+ aws ecr get-login-password | docker login ... [DRY RUN]"
    fi

    echo "=== Tagging and pushing ==="
    run docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
    run docker push "${ECR_URI}:${IMAGE_TAG}"
}

deploy_stack() {
    if [ -z "${VPC_ID:-}" ] || [ -z "${SUBNET_IDS:-}" ]; then
        echo "ERROR: VPC_ID and SUBNET_IDS must be set."
        exit 1
    fi

    echo "=== Deploying CloudFormation stack ==="
    run aws cloudformation deploy \
        --template-file deploy/aws-cloudformation.yml \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}" \
        --parameter-overrides \
            "ContainerImage=${ECR_URI}:${IMAGE_TAG}" \
            "VpcId=${VPC_ID}" \
            "SubnetIds=${SUBNET_IDS}" \
        --capabilities CAPABILITY_IAM \
        --no-fail-on-empty-changeset

    echo "=== Stack outputs ==="
    run aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}" \
        --query "Stacks[0].Outputs" \
        --output table
}

teardown() {
    echo "=== Tearing down stack ==="
    run aws cloudformation delete-stack --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
    echo "Waiting for stack deletion..."
    if [ "$DRY_RUN" != "1" ]; then
        aws cloudformation wait stack-delete-complete --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
    fi
    echo "=== Deleting ECR repository ==="
    run aws ecr delete-repository --repository-name "${ECR_REPO}" --region "${AWS_REGION}" --force
    echo "Teardown complete."
}

# --- Main ---
check_prereqs

if [ "${1:-}" = "teardown" ]; then
    teardown
else
    build_and_push
    deploy_stack
    echo ""
    echo "=== Deployment complete ==="
    echo "Run a health check:"
    echo "  curl \$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==\`ServiceURL\`].OutputValue' --output text)/health"
fi
