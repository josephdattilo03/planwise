import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.models.event import Event
from shared.services.event_service import EventService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler
from pydantic import ValidationError

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = EventService()

    if not event.get("body"):
        raise ValidationAppError()

    updated_event = json.loads(event["body"])
    print("UPDATED EVENT")
    print(updated_event)
    try:
        event_obj = Event(**updated_event)
        if not event_obj.id or not event_obj.board_id:
            print("validation error because of no id or board_id")
            raise ValidationAppError()
        service.update_event(event_obj)
    except ValidationError as e:
        print("validation error because event did not synthesize")
        raise ValidationAppError(e.errors())

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Event updated successfully",
                "event": event_obj.model_dump(mode="json"),
            }
        ),
    }

