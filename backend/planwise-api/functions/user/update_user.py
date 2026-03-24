import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.user import User
from shared.services.user_service import UserService
from shared.utils.errors import BadRequestError, ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = UserService()
    path_params = event.get("pathParameters")
    if not path_params or "id" not in path_params:
        raise BadRequestError()
    path_user_id = path_params.get("id")

    if not event.get("body"):
        raise ValidationAppError([])

    body = json.loads(event.get("body") or "{}")
    if "id" in body and body["id"] != path_user_id:
        raise ValidationAppError([{"loc": ["id"], "msg": "Path/body user id mismatch"}])
    body["id"] = path_user_id

    try:
        user_obj = User(**body)
        service.update_user(user_obj)
    except ValidationError as exc:
        raise ValidationAppError(exc.errors())

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "User updated successfully",
                "user": user_obj.model_dump(mode="json"),
            }
        ),
    }
