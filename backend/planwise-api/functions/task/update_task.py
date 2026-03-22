import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.task import Task
from shared.services.task_service import TaskService
from shared.utils.errors import NotFoundError, ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = TaskService()

    board_id = event["pathParameters"]["board_id"]
    task_id = event["pathParameters"]["id"]

    if not event.get("body"):
        raise ValidationAppError()

    body = json.loads(event.get("body"))

    try:
        # Update the task_id and board_id from path parameters to ensure consistency
        body["id"] = task_id
        body["board_id"] = board_id
        task_obj = Task(**body)
        service.update_task(task_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())
    except Exception:
        raise NotFoundError()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Task updated successfully",
                "task_id": task_obj.id,
            }
        ),
    }
