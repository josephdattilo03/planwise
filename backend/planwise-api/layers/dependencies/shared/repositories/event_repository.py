from typing import Any

from boto3.dynamodb.conditions import Key

from shared.repositories.repository import Repository
from shared.utils.db import get_table


class EventRepository(Repository):
    def __init__(self) -> None:
        self.table = get_table("event-table")

    def query_google_calendar_event_items(self, board_id: str) -> list[dict[str, Any]]:
        """One or more paginated queries: all imported Google events on this board."""
        pk = f"BOARD#{board_id}"
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(pk)
            & Key("SK").begins_with("EVENT#gcal-"),
        }
        while True:
            resp = self.table.query(**kwargs)
            items.extend(resp.get("Items") or [])
            lek = resp.get("LastEvaluatedKey")
            if not lek:
                break
            kwargs["ExclusiveStartKey"] = lek
        return items

