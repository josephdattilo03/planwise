
import json
from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.models.folder import Folder
from shared.services.folder_service import FolderService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler
from pydantic import ValidationError

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = FolderService()
    if not event.get("body"):
        raise ValidationAppError()

    updated_folder = json.loads(event.get("body"))

    try:
        folder_obj = Folder(**updated_folder)
        if not folder_obj.id or folder_obj.user_id:
            raise ValidationAppError()
        service.update_folder(folder_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())
    
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Folder updated successfully",
                "event": folder_obj.model_dump(mode="json"),
            }
        ),
    }
