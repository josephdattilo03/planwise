import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.models.event import Event
from shared.services.event_service import EventService
from shared.utils.errors import NotFoundError, ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = EventService()

    path_params = event.get("pathParameters")
    if not path_params or "id" not in path_params:
        raise ValidationAppError()

    event_id = path_params["id"]

    if not event.get("body"):
        raise ValidationAppError()

    body = json.loads(event["body"])

    existing_event = service.get_event(event_id)
    if not existing_event:
        raise NotFoundError()

    updated_data = existing_event.model_dump()
    updated_data.update(body)
    updated_data["id"] = event_id

    updated_event = Event(**updated_data)

    service.update_event(updated_event)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Event updated successfully",
                "event": updated_event.model_dump(mode="json"),
            }
        ),
    }

