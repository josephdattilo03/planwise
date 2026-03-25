import os

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.google_oauth import build_authorization_url, encode_state
from shared.utils.errors import GoogleOAuthConfigurationError, ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    params = event.get("queryStringParameters") or {}
    user_id = params.get("user_id")
    if not user_id:
        raise ValidationAppError(
            [{"loc": ["query", "user_id"], "msg": "Field required"}]
        )
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise GoogleOAuthConfigurationError()

    state = encode_state(user_id)
    location = build_authorization_url(
        GOOGLE_CLIENT_ID,
        GOOGLE_REDIRECT_URI,
        state,
    )
    return {
        "statusCode": 302,
        "headers": {"Location": location},
        "body": "",
    }
