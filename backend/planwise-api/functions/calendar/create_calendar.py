import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.calendar import Calendar
from shared.services.calendar_service import CalendarService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = CalendarService()

    try:
        # Ensure body exists
        if not event.get("body"):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"}),
            }

        # Parse and validate input
        body = json.loads(event["body"])
        calendar_obj = Calendar(**body)

        # Create calendar in DB
        service.create_calendar(calendar_obj)

        return {
            "statusCode": 201,
            "body": json.dumps(
                {
                    "message": "Calendar created successfully",
                    "calendar_id": calendar_obj.id,
                }
            ),
        }

    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": e.errors()}),
        }

    except ValueError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
