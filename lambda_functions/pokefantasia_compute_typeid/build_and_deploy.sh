#!/bin/bash
# build_and_deploy.shß
# Variables
REGION="us-east-2"
ACCOUNT_ID=REDACTED
REPO_NAME="pokecompute_typeid_repo"
IMAGE_NAME="pokefantasia-lambda"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"

# Build the Docker image with explicit platform and format
docker buildx build --provenance=false --platform=linux/amd64 -t ${IMAGE_NAME}:latest .

# Authenticate to Amazon ECR
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Tag the image for ECR
docker tag ${IMAGE_NAME}:latest ${ECR_URI}:latest

# Push the image to ECR
docker push ${ECR_URI}:latest