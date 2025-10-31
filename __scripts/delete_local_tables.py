import boto3

# Connect to local DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-east-1',
    aws_access_key_id='dummy',
    aws_secret_access_key='dummy'
)

def create_tables():
    table = dynamodb.Table("events-table")
    table.delete()
    
    print(f"Table {table.table_name} deleted successfully!")
    

if __name__ == '__main__':
    create_tables()