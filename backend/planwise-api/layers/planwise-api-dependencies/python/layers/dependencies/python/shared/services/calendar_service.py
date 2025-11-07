from typing import Any, Optional

from models.calendar import Calendar
from repositories.calendar_repository import CalendarRepository


class CalendarService:
    def __init__(self) -> None:
        self.repository = CalendarRepository()

    def create_calendar(self, calendar: Calendar) -> Calendar:
        calendar_dict = calendar.model_dump()
        self.repository.save(calendar_dict)
        return calendar

    def get_calendar(self, calendar_id: str) -> Optional[Calendar]:
        item = self.repository.find_by_id(calendar_id)

        if not item:
            return None

        return self._item_to_calendar(item)

    def update_calendar(self, calendar: Calendar) -> Calendar:
        calendar_dict = calendar.model_dump()
        self.repository.save(calendar_dict)
        return calendar

    def delete_calendar(self, calendar_id: str) -> bool:
        result: bool = self.repository.delete(calendar_id)
        return result

    def _item_to_calendar(self, item: dict[str, Any]) -> Calendar:
        try:
            calendar = Calendar.model_validate(item)
        except Exception as e:
            raise ValueError(f"Invalid calendar data from DynamoDB: {e}")
        return calendar
