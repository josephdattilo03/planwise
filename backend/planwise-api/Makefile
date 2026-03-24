.PHONY: start-local start-dynamodb create-tables build-sam zip-lambda-deployments deploy-aws deploy-aws-upload start-api stop clean health-check

AWS_ENDPOINT=http://localhost:8000
AWS_REGION=us-east-1
DUMMY_CREDS=AWS_ACCESS_KEY_ID=dummy AWS_SECRET_ACCESS_KEY=dummy

export AWS_PAGER=""

start-local: clean start-dynamodb health-check create-tables build-sam start-api

# ------------------------
# DynamoDB Local
# ------------------------
start-dynamodb:
	@echo "Starting DynamoDB Local..."
	docker compose up -d
	@echo "DynamoDB container started"

health-check:
	@echo "Waiting for DynamoDB to be ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if $(DUMMY_CREDS) aws dynamodb list-tables --endpoint-url $(AWS_ENDPOINT) --region $(AWS_REGION) > /dev/null 2>&1; then \
			echo "DynamoDB is ready!"; \
			break; \
		else \
			echo "Waiting for DynamoDB... ($$i/10)"; \
			sleep 2; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "ERROR: DynamoDB failed to start"; \
			exit 1; \
		fi; \
	done

create-tables:
	@echo "Creating DynamoDB tables..."
	@$(DUMMY_CREDS) aws dynamodb create-table \
		--table-name event-table \
		--attribute-definitions \
			AttributeName=PK,AttributeType=S \
			AttributeName=SK,AttributeType=S \
		--key-schema \
			AttributeName=PK,KeyType=HASH \
			AttributeName=SK,KeyType=RANGE \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url $(AWS_ENDPOINT) \
		--region $(AWS_REGION) \
		2>/dev/null || echo "Table 'event-table' already exists"
	@$(DUMMY_CREDS) aws dynamodb create-table \
		--table-name folder-table \
		--attribute-definitions \
			AttributeName=PK,AttributeType=S \
			AttributeName=SK,AttributeType=S \
			AttributeName=GSI1PK,AttributeType=S \
			AttributeName=GSI1SK,AttributeType=S \
		--key-schema \
			AttributeName=PK,KeyType=HASH \
			AttributeName=SK,KeyType=RANGE \
		--global-secondary-indexes \
			'[{"IndexName":"GSI1","KeySchema":[{"AttributeName":"GSI1PK","KeyType":"HASH"},{"AttributeName":"GSI1SK","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url $(AWS_ENDPOINT) \
		--region $(AWS_REGION) \
		2>/dev/null || echo "Table 'folder-table' already exists"
	@$(DUMMY_CREDS) aws dynamodb create-table \
		--table-name board-table \
		--attribute-definitions \
			AttributeName=PK,AttributeType=S \
			AttributeName=SK,AttributeType=S \
			AttributeName=GSI1PK,AttributeType=S \
			AttributeName=GSI1SK,AttributeType=S \
		--key-schema \
			AttributeName=PK,KeyType=HASH \
			AttributeName=SK,KeyType=RANGE \
		--global-secondary-indexes \
			'[{"IndexName":"GSI1","KeySchema":[{"AttributeName":"GSI1PK","KeyType":"HASH"},{"AttributeName":"GSI1SK","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url $(AWS_ENDPOINT) \
		--region $(AWS_REGION) \
		2>/dev/null || echo "Table 'board-table' already exists"
	@$(DUMMY_CREDS) aws dynamodb create-table \
		--table-name tag-table \
		--attribute-definitions \
			AttributeName=PK,AttributeType=S \
			AttributeName=SK,AttributeType=S \
		--key-schema \
			AttributeName=PK,KeyType=HASH \
			AttributeName=SK,KeyType=RANGE \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url $(AWS_ENDPOINT) \
		--region $(AWS_REGION) \
		2>/dev/null || echo "Table 'tag-table' already exists"
	@$(DUMMY_CREDS) aws dynamodb create-table \
		--table-name task-table \
		--attribute-definitions \
			AttributeName=PK,AttributeType=S \
			AttributeName=SK,AttributeType=S \
			AttributeName=GSI1PK,AttributeType=S \
		--key-schema \
			AttributeName=PK,KeyType=HASH \
			AttributeName=SK,KeyType=RANGE \
		--global-secondary-indexes \
			'[{"IndexName":"GSI1","KeySchema":[{"AttributeName":"GSI1PK","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]' \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url $(AWS_ENDPOINT) \
		--region $(AWS_REGION) \
		2>/dev/null || echo "Table 'task-table' already exists"
	@$(DUMMY_CREDS) aws dynamodb create-table \
		--table-name note-table \
		--attribute-definitions \
			AttributeName=PK,AttributeType=S \
			AttributeName=SK,AttributeType=S \
		--key-schema \
			AttributeName=PK,KeyType=HASH \
			AttributeName=SK,KeyType=RANGE \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url $(AWS_ENDPOINT) \
		--region $(AWS_REGION) \
		2>/dev/null || echo "Table 'note-table' already exists"
	@echo "Waiting for tables to be active..."
	@sleep 2

# ------------------------
# SAM Build
# ------------------------
build-sam:
	@echo "Building SAM application..."
	@sam build
	@echo "SAM build complete"

# Zip each artifact under .aws-sam/build/ into lambda-zips/<Name>.zip for manual Lambda uploads.
# Run `sam build` or `make build-sam` first. Use `sam build --use-container` for arm64 parity with AWS.
LAMBDA_ZIPS_DIR := lambda-zips
SAM_BUILD_DIR := .aws-sam/build

zip-lambda-deployments:
	@if [ ! -d "$(SAM_BUILD_DIR)" ]; then \
		echo "ERROR: $(SAM_BUILD_DIR) not found. Run 'sam build' or 'make build-sam' first."; \
		exit 1; \
	fi
	@rm -rf $(LAMBDA_ZIPS_DIR)
	@mkdir -p $(LAMBDA_ZIPS_DIR)
	@echo "Writing zips to $(LAMBDA_ZIPS_DIR)/"
	@for d in $(SAM_BUILD_DIR)/*/; do \
		[ -d "$$d" ] || continue; \
		name=$$(basename "$$d"); \
		echo "  $$name.zip"; \
		( cd "$$d" && zip -q -r "$(CURDIR)/$(LAMBDA_ZIPS_DIR)/$$name.zip" . -x "*.pyc" -x "*__pycache__*" ); \
	done
	@echo "Done."

# ------------------------
# Deploy Lambda zips to AWS (AWS CLI required)
# ------------------------
# One-shot: sam build + zip + publish layer + update every function + attach new layer version.
#   make deploy-aws
# Upload only (reuse existing lambda-zips/):
#   make deploy-aws-upload
#
# Lambda names must exist and equal $(DEPLOY_FUNCTION_PREFIX)<ZipBaseName>, e.g. CreateEventFunction.zip -> CreateEventFunction
# or DEPLOY_FUNCTION_PREFIX=planwise-api- -> planwise-api-CreateEventFunction
#
# Optional: LAMBDA_LAYER_NAME DEPLOY_FUNCTION_PREFIX AWS_REGION AWS_PROFILE
LAMBDA_LAYER_NAME ?= planwise-api-dependencies
DEPLOY_FUNCTION_PREFIX ?=

deploy-aws: build-sam zip-lambda-deployments deploy-aws-upload

deploy-aws-upload:
	@echo "Deploying from $(CURDIR)/$(LAMBDA_ZIPS_DIR) (region=$(AWS_REGION), layer=$(LAMBDA_LAYER_NAME), prefix='$(DEPLOY_FUNCTION_PREFIX)')"
	@export AWS_REGION="$(AWS_REGION)"; \
	export LAMBDA_ZIPS_DIR="$(CURDIR)/$(LAMBDA_ZIPS_DIR)"; \
	export LAMBDA_LAYER_NAME="$(LAMBDA_LAYER_NAME)"; \
	export DEPLOY_FUNCTION_PREFIX="$(DEPLOY_FUNCTION_PREFIX)"; \
	bash "$(CURDIR)/scripts/deploy_lambda_zips.sh"

# ------------------------
# SAM Local API
# ------------------------
start-api:
	@echo "Starting SAM Local API..."
	@if [ ! -d ".aws-sam/build" ]; then \
		echo "ERROR: .aws-sam/build directory not found. Run 'make build-sam' first."; \
		exit 1; \
	fi
	SAM_CLI_PARALLEL=false sam local start-api --port 3001

# ------------------------
# Cleanup
# ------------------------
stop:
	@echo "Stopping local services..."
	@docker compose down
	@pkill -f "sam local start-api" || true

clean: stop
	@echo "Cleaning SAM build artifacts..."
	@rm -rf .aws-sam

# ------------------------
# Utility Targets
# ------------------------
rebuild: clean build-sam

logs:
	@docker compose logs -f

insert-db-data:
	@python3 tests/scripts/insert_db_data.py
