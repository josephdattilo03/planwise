import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.models.board import Board 
from shared.services.board_service import BoardService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler
from pydantic import ValidationError

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = BoardService()

    if not event.get("body"):
        raise ValidationAppError()

    updated_board = json.loads(event["body"])
    try:
        board_obj = Board(**updated_board)
        if not board_obj.id or not board_obj.user_id:
            raise ValidationAppError()
        service.update_board(board_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Event updated successfully",
                "event": board_obj.model_dump(mode="json"),
            }
        ),
    }

