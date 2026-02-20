import json
from uuid import uuid4

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.task import Task
from shared.services.task_service import TaskService
from shared.utils.errors import ValidationAppError
from shared.utils.lambda_error_wrapper import lambda_http_handler


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = TaskService()

    if not event.get("body"):
        raise ValidationAppError()

    body = json.loads(event.get("body"))
    body["id"] = str(uuid4())

    try:
        task_obj = Task(**body)
        service.create_task(task_obj)
    except ValidationError as e:
        raise ValidationAppError(e.errors())

    return {
        "statusCode": 201,
        "body": json.dumps(
            {
                "message": "Task created successfully",
                "task_id": task_obj.id,
            }
        ),
    }
