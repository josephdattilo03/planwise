from shared.models.event import Event
from shared.utils.db import get_table
import json
from pydantic import ValidationError

def lambda_handler(event, context):
    try:
        table = get_table("events-table")
        body = json.loads(event['body'])
        
        event_data = Event(**body)
        item = event_data.model_dump(mode='json')
        table.put_item(Item=item)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Event created successfully',
                'event_id': event_data.id
            })
        }
    except ValidationError as e:
        return {'statusCode': 400, 'body': json.dumps({'error': e.errors()})}