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
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = NoteService()

    if not event.get("body"):
        raise ValidationAppError([])

    body = json.loads(event["body"])
    try:
        note_obj = Note(**body)
        if not note_obj.id or not note_obj.user_id:
            raise ValidationAppError([])
        service.update_note(note_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Note updated successfully",
            "note": note_obj.model_dump(mode="json"),
        }),
    }
