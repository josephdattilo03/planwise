import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.services.event_service import EventService
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = EventService()
    path_params = event.get("pathParameters")

    if not path_params or "id" not in path_params or "board_id" not in path_params:
        raise BadRequestError()

    event_id = path_params.get("id")
    board_id = path_params.get("board_id")
    event_obj = service.get_event_by_id(event_id, board_id)

    return {
        "statusCode": 200,
        "body": json.dumps(event_obj.model_dump(mode="json")),
    }


