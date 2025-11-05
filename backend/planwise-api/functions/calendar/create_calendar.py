import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.event import Event
from shared.utils.db import get_dynamodb_client, get_table


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    try:
        table = get_table("calendar-table")
        body = json.loads(event["body"])

        calendar_data = Event(**body)
        item = calendar_data.model_dump(mode="json")
        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Event created successfully", "calendar_id": calendar_data.id}
            ),
        }
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"error": e.errors()})}
