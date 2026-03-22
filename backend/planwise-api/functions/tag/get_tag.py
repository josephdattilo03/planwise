import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.models.tag import Tag
from shared.services.tag_service import TagService
from shared.utils.errors import NotFoundError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = TagService()

    user_id = event["pathParameters"]["user_id"]
    tag_id = event["pathParameters"]["id"]

    try:
        tag = service.get_tag(user_id, tag_id)
    except Exception:
        raise NotFoundError()

    return {
        "statusCode": 200,
        "body": json.dumps(tag.model_dump()),
    }
