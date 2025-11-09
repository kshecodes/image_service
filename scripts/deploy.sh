#!/usr/bin/env bash
set -euo pipefail

STACK_NAME=${STACK_NAME:-image-service}
REGION=${AWS_REGION:-us-east-1}

sam build
sam deploy --stack-name "$STACK_NAME" --region "$REGION" --capabilities CAPABILITY_IAM --confirm-changeset --no-fail-on-empty-changeset
