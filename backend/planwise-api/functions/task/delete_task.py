import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.services.task_service import TaskService
from shared.utils.errors import NotFoundError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = TaskService()

    board_id = event["pathParameters"]["board_id"]
    task_id = event["pathParameters"]["id"]

    try:
        service.delete_task(board_id, task_id)
    except Exception:
        raise NotFoundError()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Task deleted successfully",
                "task_id": task_id,
            }
        ),
    }
