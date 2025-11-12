from datetime import date
from typing import Any, List, Optional

from boto3.dynamodb.conditions import Key
from shared.utils.db import get_table


class EventsRepository:

    def __init__(self) -> None:
        self.table = get_table("events-table")

    def save(self, event_dict: dict[str, Any]) -> dict[str, Any]:
        self.table.put_item(Item=event_dict)
        return event_dict

    def find_by_id(self, event_id: str) -> Optional[dict[str, Any]]:
        response = self.table.get_item(Key={"id": event_id})
        item = response.get("Item")
        return item if isinstance(item, dict) else None

    def delete(self, event_id: str) -> bool:
        try:
            response = self.table.delete_item(
                Key={"id": event_id}, ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except Exception:
            return False

    def find_by_calendar_id(self, calendar_id: str) -> List[dict[str, Any]]:
        try:
            response = self.table.scan(
                FilterExpression="calendar_id = :cal_id",
                ExpressionAttributeValues={":cal_id": calendar_id},
            )
            items = response.get("Items", [])
            return items if isinstance(items, list) else []
        except Exception:
            return []

    def query_calendar_events_by_daterange(
        self, calendar_id: str, start: date, end: date
    ) -> List[dict[str, Any]]:
        table = get_table("events-table")

        start_bucket = f"{calendar_id}#{start.strftime('%Y:%m')}"
        end_bucket = f"{calendar_id}#{end.strftime('%Y:%m')}"
        buckets = {start_bucket, end_bucket}

        events: List[dict[str, Any]] = []
        for bucket in buckets:
            response = table.query(
                KeyConditionExpression=Key("calendar_bucket").eq(bucket)
            )
            events.extend(
                e
                for e in response["Items"]
                if e["end_time"] >= start.isoformat()
                and e["start_time"] <= end.isoformat()
            )
        return events
