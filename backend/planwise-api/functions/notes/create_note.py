import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.note import Note
from shared.services.note_service import NoteService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = NoteService()

    if not event.get("body"):
        raise ValidationAppError()

    body = json.loads(event.get("body"))


    try:
        note_obj = Note(**body)
        service.create_event(note_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())
        


    return {
        "statusCode": 201,
        "body": json.dumps(
            {
                "message": "Event created successfully",
                "event_id": note_obj.id,
            }
        ),
    }

