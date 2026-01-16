.PHONY: start-local create-tables start-api

start-local: start-dynamodb create-tables start-api

start-dynamodb:
	@echo "Starting DynamoDB Local..."
	docker compose up -d
	@sleep 3

create-tables:
	@echo "Creating tables..."
	@AWS_ACCESS_KEY_ID=dummy AWS_SECRET_ACCESS_KEY=dummy aws dynamodb create-table \
		--table-name YourTableName \
		--attribute-definitions AttributeName=id,AttributeType=S \
		--key-schema AttributeName=id,KeyType=HASH \
		--billing-mode PAY_PER_REQUEST \
		--endpoint-url http://localhost:8000 \
		--region us-east-1 || echo "Table may already exist"

start-api:
	@echo "Starting SAM Local API..."
	rm -rf .aws-sam
	docker system prune -f
	sam build --cached
	sam local start-api --warm-containers LAZY

stop:
	rm -rf .aws-sam
	docker system prune -f
	docker compose down