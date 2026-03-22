import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.tag import Tag
from shared.services.tag_service import TagService
from shared.utils.errors import NotFoundError, ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = TagService()

    user_id = event["pathParameters"]["user_id"]
    tag_id = event["pathParameters"]["id"]

    if not event.get("body"):
        raise ValidationAppError()

    body = json.loads(event.get("body"))

    try:
        # Update the tag_id and user_id from path parameters to ensure consistency
        body["id"] = tag_id
        body["user_id"] = user_id
        tag_obj = Tag(**body)
        service.update_tag(tag_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())
    except Exception:
        raise NotFoundError()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Tag updated successfully",
                "tag_id": tag_obj.id,
            }
        ),
    }
