import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from pydantic import ValidationError
from shared.models.board import Board 
from shared.services.board_service import BoardService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> APIGatewayProxyResponseV2:
    service = BoardService()

    try:
        if not event.get("body"):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"}),
            }

        body = json.loads(event["body"])

        board_obj = Board(**body)

        service.create_board(board_obj)

        return {
            "statusCode": 201,
            "body": json.dumps(
                {
                    "message": "Board created successfully",
                    "event_id": board_obj.id,
                }
            ),
        }

    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": e.errors()}),
        }

    except ValueError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
