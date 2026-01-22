
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

    if not path_params or "user_id" not in path_params or "depth" not in path_params or "path" not in path_params:
        raise BadRequestError()

    user_id = path_params.get("user_id")
    depth = path_params.get("depth")
    path = path_params.get("path")
    folder_objs = service.get_folders_at_depth(user_id, depth, path)
    return {
        "statusCode": 200,
        "body": json.dumps([folder.model_dump(mode="json") for folder in folder_objs]),
    }
