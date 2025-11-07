from typing import Any, List, Optional

from utils.db import get_table


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

    # def query_by_calendar_and_time_range(
    #     self,
    #     calendar_id: str,
    #     start_date: str,
    #     end_date: str
    # ) -> List[dict]:
    #     response = self.table.query(
    #         IndexName='calendar_id-start_time-index',
    #         KeyConditionExpression='calendar_id = :cal_id
    # AND start_time <= :end_date',
    #         FilterExpression='end_time >= :start_date',
    #         ExpressionAttributeValues={
    #             ':cal_id': calendar_id,
    #             ':start_date': start_date,
    #             ':end_date': end_date
    #         }
    #     )
    #     return response.get('Items', [])
