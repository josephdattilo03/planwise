
import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.services.board_service import BoardService
from shared.utils.lambda_error_wrapper import lambda_http_handler
from shared.utils.errors import BadRequestError

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = BoardService()

    path_params = event.get("pathParameters")
    if not path_params or "id" not in path_params or "user_id" not in path_params:
        raise BadRequestError()

    board_id = path_params.get("id")
    user_id = path_params.get("user_id")

    service.delete_board(board_id, user_id)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "Board deleted successfully", "board_id": board_id}
        ),
    }

