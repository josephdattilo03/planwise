import json

from botocore.exceptions import ClientError
from shared.utils.db import get_table


def lambda_handler(event, context):
    try:
        table = get_table("events-table")

        # Extract event ID from path parameters
        event_id = event["pathParameters"]["id"]

        # Parse request body
        body = json.loads(event["body"])

        # Check if event exists
        response = table.get_item(Key={"id": event_id})
        if "Item" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Event not found"})}

        # Build update expression dynamically
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}

        # List of updatable fields (exclude id since it's the key)
        updatable_fields = [
            "calendar_id",
            "start_time",
            "end_time",
            "event_color",
            "is_all_day",
            "description",
            "location",
            "timezone",
            "recurrence",
        ]

        update_parts = []
        for field in updatable_fields:
            if field in body:
                # Use expression attribute names to handle reserved keywords
                attr_name = f"#{field}"
                attr_value = f":{field}"
                expression_attribute_names[attr_name] = field
                expression_attribute_values[attr_value] = body[field]
                update_parts.append(f"{attr_name} = {attr_value}")

        if not update_parts:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No valid fields to update"}),
            }

        update_expression += ", ".join(update_parts)

        # Update the item
        updated_response = table.update_item(
            Key={"id": event_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Event updated successfully",
                    "event": updated_response["Attributes"],
                }
            ),
        }
    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing event ID in path parameters"}),
        }
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
