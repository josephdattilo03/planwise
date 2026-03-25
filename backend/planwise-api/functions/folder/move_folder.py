import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.services.folder_service import FolderService
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = FolderService()
    path_params = event.get("pathParameters")
    if not path_params or "id" not in path_params or "user_id" not in path_params:
        err = BadRequestError()
        err.message = "Missing path parameters"
        raise err

    folder_id = path_params.get("id")
    user_id = path_params.get("user_id")

    body = json.loads(event.get("body") or "{}")
    new_parent_id = body.get("new_parent_folder_id")
    if not new_parent_id or not isinstance(new_parent_id, str):
        err = BadRequestError()
        err.message = "new_parent_folder_id is required"
        raise err

    folder = service.move_folder(user_id, folder_id, new_parent_id)
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Folder moved successfully",
                "folder": folder.model_dump(mode="json") if folder else None,
            }
        ),
    }
