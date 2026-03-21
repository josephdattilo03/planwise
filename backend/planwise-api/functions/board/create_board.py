
import json
from uuid import uuid4

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.board import Board
from shared.services.board_service import BoardService
from shared.services.folder_service import FolderService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = BoardService()
    folder_service = FolderService()

    if not event.get("body"):
        raise ValidationAppError()

    body = json.loads(event.get("body"))
    if not body.get("id"):
        body["id"] = str(uuid4())


    try:
        board_obj = Board(**body)
        folder_service.ensure_root_folder(board_obj.user_id)
        service.create_board(board_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())
        


    return {
        "statusCode": 201,
        "body": json.dumps(
            {
                "message": "Board created successfully",
                "board_id": board_obj.id,
            }
        ),
    }

