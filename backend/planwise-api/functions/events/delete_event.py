import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from botocore.exceptions import ClientError
from shared.services.event_service import EventService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = EventService()

    try:
        path_params = event.get("pathParameters")
        if not path_params or "id" not in path_params:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing event ID in path parameters"}),
            }

        event_id = path_params["id"]

        existing_event = service.get_event(event_id)
        if not existing_event:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Event not found"}),
            }

        deleted = service.delete_event(event_id)
        if not deleted:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to delete event"}),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Event deleted successfully", "event_id": event_id}
            ),
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": e.response["Error"]["Message"]}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
