import json

from botocore.exceptions import ClientError
from shared.utils.db import get_table


def lambda_handler(event, context):
    try:
        calendar_table = get_table("calendar-table")
        event_table = get_table("event-table")


        # Extract calendar ID from path parameters
        calendar_id = event["pathParameters"]["id"]

        # Check if ca;emdar exists before deleting
        response = calendar_table.get_item(Key={"id": calendar_id})
        if "Item" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Calendar not found"})}

        # Delete events in that calendar
        deleted_events = 0
        scan_params = {
            "FilterExpression": "calendar_id = :cal_id",
            "ExpressionAttributeValues": {":cal_id": calendar_id}
        }

        while True:
            events_response = event_table.scan(**scan_params)
            
            # Delete each matching event
            for item in events_response.get("Items", []):
                event_table.delete_item(Key={"id": item["id"]})
                deleted_events += 1
            
            # Check if there are more items to scan
            if "LastEvaluatedKey" not in events_response:
                break
            scan_params["ExclusiveStartKey"] = events_response["LastEvaluatedKey"]

        # Delete the calendar
        calendar_table.delete_item(Key={"id": calendar_id})

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Calendar deleted successfully", 
                 "calendar_id": calendar_id,
                 "events_deleted": deleted_events}
            ),
        }
    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing calendar ID in path parameters"}),
        }
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
