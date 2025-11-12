import os

import boto3
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table

DYNAMO_URL = os.environ.get("DYNAMODB_URL", "http://host.docker.internal:8000")


def get_dynamodb_client() -> DynamoDBServiceResource:
    return boto3.resource(
        "dynamodb",
        region_name="us-east-1",
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
        endpoint_url=DYNAMO_URL,
    )


def get_table(table_name: str) -> Table:
    dynamodb = get_dynamodb_client()
    return dynamodb.Table(table_name)
