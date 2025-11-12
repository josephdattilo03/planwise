import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from botocore.exceptions import ClientError
from pydantic import ValidationError
from shared.models.calendar import Calendar
from shared.services.calendar_service import CalendarService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = CalendarService()

    try:
        # Extract calendar ID from path parameters
        path_params = event.get("pathParameters")
        if not path_params or "id" not in path_params:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing calendar ID in path parameters"}),
            }

        calendar_id = path_params["id"]

        # Parse body
        if not event.get("body"):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"}),
            }

        body = json.loads(event["body"])

        # Fetch the existing calendar
        existing_calendar = service.get_calendar(calendar_id)
        if existing_calendar is None:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Calendar not found"}),
            }

        # Merge updates with existing fields
        updated_data = existing_calendar.model_dump()
        updated_data.update(body)

        # Validate and update
        updated_calendar = Calendar(**updated_data)
        saved_calendar = service.update_calendar(updated_calendar)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Calendar updated successfully",
                    "calendar": saved_calendar.model_dump(mode="json"),
                }
            ),
        }

    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": e.errors()}),
        }

    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
