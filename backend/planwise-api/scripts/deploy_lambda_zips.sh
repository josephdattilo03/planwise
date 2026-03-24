#!/usr/bin/env bash
# Publish DependenciesLayer.zip as a new layer version, then update every function
# zip in LAMBDA_ZIPS_DIR (except DependenciesLayer) with code + that layer.
#
# Env (set by Makefile or your shell):
#   LAMBDA_ZIPS_DIR   absolute path to lambda-zips/
#   AWS_REGION
#   LAMBDA_LAYER_NAME name for publish-layer-version (e.g. planwise-api-dependencies)
#   DEPLOY_FUNCTION_PREFIX optional prefix for Lambda function names (e.g. planwise-api-)
#
# Function name = ${DEPLOY_FUNCTION_PREFIX}$(basename zip .zip)
# e.g. CreateEventFunction.zip -> CreateEventFunction or planwise-api-CreateEventFunction

set -euo pipefail

export AWS_PAGER=""

: "${LAMBDA_ZIPS_DIR:?Set LAMBDA_ZIPS_DIR to absolute path of lambda-zips}"
: "${AWS_REGION:=us-east-1}"
LAMBDA_LAYER_NAME="${LAMBDA_LAYER_NAME:-planwise-api-dependencies}"
DEPLOY_FUNCTION_PREFIX="${DEPLOY_FUNCTION_PREFIX:-}"

LAYER_ZIP="${LAMBDA_ZIPS_DIR}/DependenciesLayer.zip"
if [[ ! -f "$LAYER_ZIP" ]]; then
  echo "ERROR: Missing layer zip: $LAYER_ZIP"
  exit 1
fi

echo "Publishing layer ${LAMBDA_LAYER_NAME} from $(basename "$LAYER_ZIP") ..."
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name "$LAMBDA_LAYER_NAME" \
  --description "planwise-api dependencies (make deploy-aws)" \
  --zip-file "fileb://${LAYER_ZIP}" \
  --compatible-runtimes python3.13 \
  --compatible-architectures arm64 \
  --region "$AWS_REGION" \
  --query 'LayerVersionArn' \
  --output text)

echo "LayerVersionArn=$LAYER_ARN"

shopt -s nullglob
zips=("${LAMBDA_ZIPS_DIR}"/*.zip)
if [[ ${#zips[@]} -eq 0 ]]; then
  echo "ERROR: No zips in ${LAMBDA_ZIPS_DIR}"
  exit 1
fi

for zip_path in "${zips[@]}"; do
  base=$(basename "$zip_path" .zip)
  if [[ "$base" == "DependenciesLayer" ]]; then
    continue
  fi
  func_name="${DEPLOY_FUNCTION_PREFIX}${base}"
  echo "Updating function: $func_name"
  aws lambda update-function-code \
    --function-name "$func_name" \
    --zip-file "fileb://${zip_path}" \
    --region "$AWS_REGION"
  aws lambda wait function-updated --function-name "$func_name" --region "$AWS_REGION"
  aws lambda update-function-configuration \
    --function-name "$func_name" \
    --layers "$LAYER_ARN" \
    --region "$AWS_REGION"
  aws lambda wait function-updated --function-name "$func_name" --region "$AWS_REGION"
done

echo "Done. All functions updated and attached to $LAYER_ARN"
