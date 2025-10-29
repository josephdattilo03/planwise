import boto3

def get_dynamodb_client():
    return boto3.resource(
        'dynamodb',
        region_name='us-east-1',
        endpoint_url='http://localhost:8000' # local setup
    )

def get_table(table_name: str):
    dynamodb = get_dynamodb_client()
    return dynamodb.Table(table_name)
