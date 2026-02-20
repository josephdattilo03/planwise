
import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.services.tag_service import TagService
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = TagService()
    path_params = event.get("pathParameters")

    if not path_params or "user_id" not in path_params:
        raise BadRequestError()

    user_id = path_params.get("user_id")
    board_objs = service.get_tags_by_user_id(user_id)
    return {
        "statusCode": 200,
        "body": json.dumps([board.model_dump(mode="json") for board in board_objs]),
    }
