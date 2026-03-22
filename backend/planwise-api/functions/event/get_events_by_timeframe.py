import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.services.event_service import EventService
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler

@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = EventService()
    path_params = event.get("pathParameters")

    if not path_params or "start_time" not in path_params or "end_time" not in path_params:
        raise BadRequestError()

    start_time = path_params.get("start_time")
    end_time = path_params.get("end_time")
    event_objs = []
    return {
        "statusCode": 200,
        "body": json.dumps([event.model_dump(mode="json") for event in event_objs]),
    }
