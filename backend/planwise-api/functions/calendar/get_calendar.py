import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from botocore.exceptions import ClientError
from shared.utils.db import get_table


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    try:
        table = get_table("calendars-table")

        # Extract calendar ID from path parameters
        calendar_id = event["pathParameters"]["id"]

        # Get the calendar from DynamoDB
        response = table.get_item(Key={"id": calendar_id})

        if "Item" not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Calendar not found"}),
            }

        return {"statusCode": 200, "body": json.dumps(response["Item"])}
    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing calendar ID in path parameters"}),
        }
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
