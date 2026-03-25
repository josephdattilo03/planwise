# shared/utils/lambda_wrapper.py

import json
from typing import Callable

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.utils.errors import AppError


def lambda_http_handler(
    fn: Callable[
        [lambda_events.APIGatewayProxyEventV2, lambda_context.Context],
        APIGatewayProxyResponseV2,
    ],
) -> Callable[
    [lambda_events.APIGatewayProxyEventV2, lambda_context.Context],
    APIGatewayProxyResponseV2,
]:
    def wrapper(
        event: lambda_events.APIGatewayProxyEventV2,
        context: lambda_context.Context,
    ) -> APIGatewayProxyResponseV2:
        try:
            return fn(event, context)

        except AppError as e:
            return e.to_response()

        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Internal server error: {e}"}),
            }

    return wrapper
