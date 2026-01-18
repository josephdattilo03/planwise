from typing import Any, Optional

from shared.models.event import Event
from shared.repositories.event_repository import EventRepository
from shared.utils.errors import InvalidEventTimeError


class EventService:

    def __init__(self) -> None:
        self.repository = EventRepository()

    def create_event(self, event: Event) -> Event:
        if event.start_time > event.end_time:
            raise InvalidEventTimeError()

        event_dict = event.model_dump()

        if event.recurrence is not None:
            event_dict["recurrence"] = event.recurrence.model_dump()

        self.repository.save(event_dict)
        return event

    def get_event(self, event_id: str, board_id: str) -> Optional[Event]:
        print("about to look for the event")
        item = self.repository.get_by_id_pair(f"BOARD#{board_id}", f"EVENT#{event_id}")
        return self._item_to_event(item)

    def update_event(self, event: Event) -> Event:
        print("about to check about the whole time thing")
        if event.start_time > event.end_time:
            raise InvalidEventTimeError()
        
        print("model dumping")

        event_dict = event.model_dump()
        if event.recurrence is not None:
            event_dict["recurrence"] = event.recurrence.model_dump()
        print("about to update the event by id pair")
        self.repository.update_by_id_pair(event_dict)
        return event

    def delete_event(self, event_id: str, board_id: str):
        self.repository.delete_by_id_pair(f"BOARD#{board_id}", f"EVENT#{event_id}")

    def _item_to_event(self, item: dict[str, Any]) -> Event:
        try:
            event = Event(**item)
        except Exception as e:
            raise ValueError(f"Invalid event data from DynamoDB: {e}")

        return event
