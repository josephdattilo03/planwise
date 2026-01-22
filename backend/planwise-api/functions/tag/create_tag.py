import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.tag import Tag
from shared.services.tag_service import TagService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = TagService()

    if not event.get("body"):
        raise ValidationAppError()

    body = json.loads(event.get("body"))

    try:
        tag_obj = Tag(**body)
        service.create_tag(tag_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())

    return {
        "statusCode": 201,
        "body": json.dumps(
            {
                "message": "Tag created successfully",
                "tag_id": tag_obj.id,
            }
        ),
    }
