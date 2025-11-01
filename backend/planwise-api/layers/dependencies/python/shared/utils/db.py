import boto3
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table


def get_dynamodb_client() -> DynamoDBServiceResource:
    return boto3.resource(
        "dynamodb",
        region_name="us-east-1",
        endpoint_url="http://localhost:8000",  # local setup
    )


def get_table(table_name: str) -> Table:
    dynamodb = get_dynamodb_client()
    return dynamodb.Table(table_name)
