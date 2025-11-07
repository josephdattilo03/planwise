import json
from datetime import date

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing import responses as lambda_response
from shared.models.event import Event, Recurrence
from shared.utils.db import get_table


def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2, context: lambda_context.Context
) -> lambda_response.APIGatewayProxyResponseV2:
    table = get_table("events-table")

    path_params = event.get("pathParameters", {})
    calendar_id = path_params.get("calendar_id")
    query_params = event.get("queryStringParameters", {})
    if not (start_date := query_params.get("start_date")) or not (
        end_date := query_params.get("end_date")
    ):
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": "start_date and end_date query parameters are required",
                    "example": """/calendars/cal_123/events?start_
                    date=2025-11-01&end_date=2025-11-30""",
                }
            ),
        }

    # Query using the GSI with start_time as range key
    response = table.query(
        IndexName="calendar_id-start_time-index",
        KeyConditionExpression="calendar_id = :cal_id AND start_time <= :end_date",
        FilterExpression="end_time >= :start_date",
        ExpressionAttributeValues={
            ":cal_id": calendar_id,
            ":start_date": start_date.isoformat(),
            ":end_date": end_date.isoformat(),
        },
    )

    # Convert response items to Event objects
    events = []
    for item in response.get("Items", []):
        # Convert date strings back to date objects
        item["start_time"] = date.fromisoformat(item["start_time"])
        item["end_time"] = date.fromisoformat(item["end_time"])

        # Handle recurrence if present
        if item.get("recurrence"):
            rec = item["recurrence"]
            rec["date_until"] = date.fromisoformat(rec["date_until"])
            if rec.get("date_start"):
                rec["date_start"] = date.fromisoformat(rec["date_start"])
            item["recurrence"] = Recurrence(**rec)

        events.append(Event(**item))

    return events
