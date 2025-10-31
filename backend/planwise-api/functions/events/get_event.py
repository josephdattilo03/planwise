from layers.dependencies.python.shared.utils.db import get_table
import json
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    try:
        table = get_table("events-table")
        
        # Extract event ID from path parameters
        event_id = event['pathParameters']['id']
        
        # Get the event from DynamoDB
        response = table.get_item(Key={'id': event_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Event not found'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response['Item'])
        }
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing event ID in path parameters'})
        }
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
