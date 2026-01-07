import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from botocore.exceptions import ClientError
from shared.services.calendar_service import CalendarService
from shared.services.event_service import EventsService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    calendar_service = CalendarService()
    event_service = EventsService()

    try:
        # Extract calendar ID from path parameters
        path_params = event.get("pathParameters")
        if not path_params or "id" not in path_params:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing calendar ID in path parameters"}),
            }

        calendar_id = path_params["id"]

        # Check if calendar exists
        calendar = calendar_service.get_calendar(calendar_id)
        if calendar is None:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Calendar not found"}),
            }

        # Delete all events associated with this calendar
        deleted_events = 0
        events = event_service.repository.find_by_calendar_id(calendar_id)
        for event_item in events:
            if "id" in event_item:
                deleted = event_service.delete_event(event_item["id"])
                if deleted:
                    deleted_events += 1

        # Delete the calendar
        deleted_calendar = calendar_service.delete_calendar(calendar_id)
        if not deleted_calendar:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to delete calendar"}),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Calendar deleted successfully",
                    "calendar_id": calendar_id,
                    "events_deleted": deleted_events,
                }
            ),
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
