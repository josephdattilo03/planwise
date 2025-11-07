from typing import Any, Optional

from models.event import Event
from repositories.events_repository import EventsRepository


class EventsService:

    def __init__(self) -> None:
        self.repository = EventsRepository()

    def create_event(self, event: Event) -> Event:
        if event.start_time > event.end_time:
            raise ValueError("Start time must be before end time")

        event_dict = event.model_dump()

        if event_dict.get("recurrence"):
            event_dict["recurrence"] = event.recurrence.model_dump()

        self.repository.save(event_dict)
        return event

    def get_event(self, event_id: str) -> Optional[Event]:
        item = self.repository.find_by_id(event_id)

        if not item:
            return None

        return self._item_to_event(item)

    def update_event(self, event: Event) -> Event:
        if event.start_time > event.end_time:
            raise ValueError("Start time must be before end time")

        event_dict = event.model_dump()

        if event_dict.get("recurrence"):
            event_dict["recurrence"] = event.recurrence.model_dump()

        self.repository.save(event_dict)
        return event

    def delete_event(self, event_id: str) -> bool:
        result: bool = self.repository.delete(event_id)
        return result

    def _item_to_event(self, item: dict[str, Any]) -> Event:
        try:
            event = Event.model_validate(item)
        except Exception as e:
            raise ValueError(f"Invalid event data from DynamoDB: {e}")

        return event
