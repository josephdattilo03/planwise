import json
from typing import Any

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from botocore.exceptions import ClientError
from shared.services.calendar_service import CalendarService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = CalendarService()

    try:
        path_params = event.get("pathParameters")
        if not path_params or "id" not in path_params:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing calendar ID in path parameters"}),
            }

        calendar_id = path_params["id"]

        # Fetch calendar
        calendar: dict[str, Any] | None = service.find_by_id(calendar_id)

        if calendar is None:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Calendar not found"}),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(calendar),
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
