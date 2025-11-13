from datetime import date
from typing import Any, List, Optional

from boto3.dynamodb.conditions import Attr, Key
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
            response = self.table.query(
                IndexName="calendar_id-start_time-index",
                KeyConditionExpression=Key("calendar_id").eq(calendar_id),
            )

            items: List[dict[str, Any]] = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = self.table.query(
                    IndexName="calendar_id-start_time-index",
                    KeyConditionExpression=Key("calendar_id").eq(calendar_id),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            return items
        except Exception:
            return []

    def query_calendar_events_by_daterange(
        self, calendar_id: str, start: date, end: date
    ) -> List[dict[str, Any]]:
        try:
            query_start_iso = start.isoformat()
            query_end_iso = end.isoformat()

            response = self.table.query(
                IndexName="calendar_id-start_time-index",
                KeyConditionExpression=(
                    Key("calendar_id").eq(calendar_id)
                    & Key("start_time").lt(query_end_iso)
                ),
                FilterExpression=Attr("end_time").gt(query_start_iso),
            )

            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = self.table.query(
                    IndexName="calendar_id-start_time-index",
                    KeyConditionExpression=(
                        Key("calendar_id").eq(calendar_id)
                        & Key("start_time").lt(query_end_iso)
                    ),
                    FilterExpression=Attr("end_time").gt(query_start_iso),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            return items if isinstance(items, list) else []

        except Exception as e:
            print(f"Error querying events: {e}")
            return []
