import json

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

        calendar_obj = service.get_calendar(calendar_id)

        if not calendar_obj:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Calendar not found"}),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(calendar_obj.model_dump(mode="json")),
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
