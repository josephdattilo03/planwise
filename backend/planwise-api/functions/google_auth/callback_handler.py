import json
import os
from urllib.parse import urlencode

import requests
from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.google_oauth import (
    access_token_expiry_epoch,
    decode_state,
    exchange_code_for_tokens,
)
from shared.services.user_service import UserService
from shared.utils.errors import (
    BadRequestError,
    GoogleOAuthConfigurationError,
    NotFoundError,
    ValidationAppError,
)
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "")
    frontend_success = os.environ.get("FRONTEND_AUTH_SUCCESS_URI", "")

    if not client_id or not client_secret or not redirect_uri or not frontend_success:
        raise GoogleOAuthConfigurationError()

    params = event.get("queryStringParameters") or {}
    if params.get("error"):
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": params.get("error"),
                    "error_description": params.get("error_description", ""),
                }
            ),
        }

    code = params.get("code")
    state = params.get("state")
    if not code or not state:
        raise BadRequestError()
    try:
        user_id = decode_state(state)
    except ValueError:
        raise ValidationAppError([{"loc": ["query", "state"], "msg": "Invalid state"}])

    try:
        token_payload = exchange_code_for_tokens(
            code, client_id, client_secret, redirect_uri
        )
    except requests.HTTPError as exc:
        detail = ""
        if exc.response is not None:
            detail = exc.response.text[:800]
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "token_exchange_failed", "detail": detail}),
        }

    access = token_payload.get("access_token")
    if not access:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "missing_access_token"}),
        }

    service = UserService()
    try:
        user = service.get_user_by_id(user_id)
    except NotFoundError:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "user_not_found", "user_id": user_id}),
        }

    refresh = token_payload.get("refresh_token")
    if refresh:
        user.google_refresh_token = refresh

    user.google_access_token = access
    user.google_token_expiry = access_token_expiry_epoch(token_payload.get("expires_in"))

    service.update_user(user)

    redirect_url = (
        f"{frontend_success}?"
        f"{urlencode({'user_id': user_id, 'google_connected': 'true'})}"
    )
    return {
        "statusCode": 302,
        "headers": {"Location": redirect_url},
        "body": "",
    }
