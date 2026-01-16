from shared.utils.db import get_table
from typing import Any, Optional

class Repository:

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