.PHONY: start-local start-dynamodb create-tables build-sam start-api stop clean health-check

AWS_ENDPOINT=http://localhost:8000
AWS_REGION=us-east-1
DUMMY_CREDS=AWS_ACCESS_KEY_ID=dummy AWS_SECRET_ACCESS_KEY=dummy

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
	@echo "Waiting for table to be active..."
	@sleep 2

# ------------------------
# SAM Build
# ------------------------
build-sam:
	@echo "Building SAM application..."
	@sam build
	@echo "SAM build complete"

# ------------------------
# SAM Local API
# ------------------------
start-api:
	@echo "Starting SAM Local API..."
	@if [ ! -d ".aws-sam/build" ]; then \
		echo "ERROR: .aws-sam/build directory not found. Run 'make build-sam' first."; \
		exit 1; \
	fi
	SAM_CLI_PARALLEL=false sam local start-api

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