import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from botocore.exceptions import ClientError
from shared.services.board_service import BoardService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = BoardService()

    try:
        path_params = event.get("pathParameters")
        if not path_params or "id" not in path_params:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing event ID in path parameters"}),
            }

        board_id = path_params["id"]

        existing_event = service.get_event(board_id)
        if not existing_event:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Board not found"}),
            }

        deleted = service.delete_event(board_id)
        if not deleted:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to delete board"}),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Event deleted successfully", "board_id": board_id}
            ),
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": e.response["Error"]["Message"]}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
