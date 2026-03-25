import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.user import User
from shared.services.user_service import UserService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = UserService()

    if not event.get("body"):
        raise ValidationAppError([])

    body = json.loads(event.get("body") or "{}")
    try:
        user_obj = User(**body)
        service.create_user(user_obj)
    except ValidationError as exc:
        raise ValidationAppError(exc.errors())

    return {
        "statusCode": 201,
        "body": json.dumps(
            {
                "message": "User created successfully",
                "user_id": user_obj.id,
            }
        ),
    }
