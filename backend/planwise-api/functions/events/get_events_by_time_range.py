from layers.dependencies.python.shared.utils.db import get_table
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    try:
        table = get_table("events-table")
        
        # Extract query parameters
        query_params = event.get('queryStringParameters', {})
        
        if not query_params or 'start_time' not in query_params or 'end_time' not in query_params:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required query parameters: start_time and end_time'
                })
            }
        
        start_time = query_params['start_time']
        end_time = query_params['end_time']
        
        # Scan table with filter expression
        # Get events where the event's time range overlaps with the query range
        # Event overlaps if: event_start <= query_end AND event_end >= query_start
        filter_expression = Attr('start_time').lte(end_time) & Attr('end_time').gte(start_time)
        
        response = table.scan(
            FilterExpression=filter_expression
        )
        
        events = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expression,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            events.extend(response.get('Items', []))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'events': events,
                'count': len(events)
            })
        }
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Unexpected error: {str(e)}'})
        }
