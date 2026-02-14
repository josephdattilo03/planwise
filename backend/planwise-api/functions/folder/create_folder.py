from shared.utils.lambda_error_wrapper import lambda_http_handler
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from aws_lambda_typing import events as lambda_events
import json
from aws_lambda_typing import context as lambda_context
from shared.services.folder_service import FolderService
from shared.utils.errors import ValidationAppError
from shared.models.folder import Folder
from pydantic import ValidationError

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = FolderService()

    if not event.get("body"):
        raise ValidationAppError()
    
    body = json.loads(event.get("body"))
    
    try:
        folder_object = Folder(**body)
        service.create_folder(folder_object)
        # create with service here
    except ValidationError as e:
        raise ValidationAppError(e.errors())

    return {
        "statusCode": 201,
        "body": json.dumps(
            {
                "message": "Folder created successfully",
                "event_id": folder_object.id,
            }
        ),
    }