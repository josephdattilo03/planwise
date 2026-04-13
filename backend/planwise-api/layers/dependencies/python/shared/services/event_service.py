from typing import Any, List, Optional, Set

from pydantic import ValidationError

from shared.models.event import Event
from shared.repositories.event_repository import EventRepository
from shared.utils.errors import InvalidEventTimeError, ValidationAppError


class EventService:

    def __init__(self) -> None:
        self.repository = EventRepository()

    def get_google_calendar_event_ids(self, board_id: str) -> Set[str]:
        """Single logical read path: query only SK prefix EVENT#gcal- for this board."""
        items = self.repository.query_google_calendar_event_items(board_id)
        return {str(i["id"]) for i in items if i.get("id")}

    def create_events_batch(self, events: list[Event]) -> None:
        if not events:
            return
        with self.repository.table.batch_writer() as batch:
            for event in events:
                if event.start_time > event.end_time:
                    raise InvalidEventTimeError()
                event_dict = event.model_dump()
                if event.recurrence is not None:
                    event_dict["recurrence"] = event.recurrence.model_dump()
                batch.put_item(Item=event_dict)

    def create_event(self, event: Event) -> Event:
        if event.start_time > event.end_time:
            raise InvalidEventTimeError()

        event_dict = event.model_dump()

        if event.recurrence is not None:
            event_dict["recurrence"] = event.recurrence.model_dump()

        self.repository.save(event_dict)
        return event

    def get_event_by_id(self, event_id: str, board_id: str) -> Optional[Event]:
        item = self.repository.get_by_id_pair(f"BOARD#{board_id}", f"EVENT#{event_id}")
        return self._item_to_event(item)

    def get_event_by_board(self, board_id: str) -> Optional[List[Event]]:
        items = self.repository.get_pk_list(f"BOARD#{board_id}")
        return [self._item_to_event(item) for item in items]

    def update_event(self, event: Event) -> Event:
        if event.start_time > event.end_time:
            raise InvalidEventTimeError()
        

        event_dict = event.model_dump()
        if event.recurrence is not None:
            event_dict["recurrence"] = event.recurrence.model_dump()
        self.repository.update_by_id_pair(event_dict)
        return event

    def delete_event(self, event_id: str, board_id: str):
        self.repository.delete_by_id_pair(f"BOARD#{board_id}", f"EVENT#{event_id}")

    def _item_to_event(self, item: dict[str, Any]) -> Event:
        try:
            event = Event(**item)
        except ValidationError as e:
            raise ValidationAppError(e.errors())
        return event
