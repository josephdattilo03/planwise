import json
from datetime import date

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.services.events_service import EventsService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = EventsService()

    try:
        path_params = event.get("pathParameters", {}) or {}
        calendar_id = path_params.get("calendar_id")
        query_params = event.get("queryStringParameters", {}) or {}

        if not calendar_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing calendar_id in path"}),
            }

        start_str = query_params.get("start_date")
        end_str = query_params.get("end_date")

        if not start_str or not end_str:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "start_date & end_date query parameters are required",
                        "example": (
                            f"/calendars/{calendar_id}/events?"
                            "start_date=2025-11-01&end_date=2025-11-30"
                        ),
                    }
                ),
            }

        try:
            start_date = date.fromisoformat(start_str)
            end_date = date.fromisoformat(end_str)
        except ValueError:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Dates must be in ISO format (YYYY-MM-DD)"}
                ),
            }

        events = service.get_events_from_date_range(calendar_id, start_date, end_date)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": f"Retrieved {len(events)} events",
                    "events": [e.model_dump() for e in events],
                },
                default=str,  # Handles date serialization
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
