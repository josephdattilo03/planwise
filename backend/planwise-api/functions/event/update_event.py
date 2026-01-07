import json

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from botocore.exceptions import ClientError
from pydantic import ValidationError
from shared.models.event import Event
from shared.services.event_service import EventService


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    service = EventService()

    try:
        path_params = event.get("pathParameters")
        if not path_params or "id" not in path_params:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing event ID in path parameters"}),
            }

        event_id = path_params["id"]

        if not event.get("body"):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"}),
            }

        body = json.loads(event["body"])

        existing_event = service.get_event(event_id)
        if not existing_event:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Event not found"}),
            }

        updated_data = existing_event.model_dump()
        updated_data.update(body)
        updated_data["id"] = event_id

        updated_event = Event(**updated_data)

        service.update_event(updated_event)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Event updated successfully",
                    "event": updated_event.model_dump(mode="json"),
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
