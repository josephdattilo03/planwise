import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from layers.dependencies.python.shared.models import Event
from layers.dependencies.python.shared.utils.db import get_table
from pydantic import ValidationError


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    try:
        table = get_table("events-table")
        body = json.loads(event["body"])

        event_data = Event(**body)
        item = event_data.model_dump(mode="json")
        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Event created successfully", "event_id": event_data.id}
            ),
        }
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"error": e.errors()})}
