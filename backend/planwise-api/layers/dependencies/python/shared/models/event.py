from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, FieldSerializationInfo, field_serializer


class Recurrence(BaseModel):
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    day_of_week: List[
        Literal[
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ]
    ]
    date_until: date
    date_start: Optional[date] = None

    @field_serializer("date_until", "date_start")
    def serialize_date(
        self, value: Optional[date], _info: FieldSerializationInfo
    ) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()


class Event(BaseModel):
    id: str
    calendar_id: str
    start_time: date
    end_time: date
    event_color: str
    is_all_day: bool
    description: str
    location: str
    timezone: str
    recurrence: Optional[Recurrence] = None

    @field_serializer("start_time", "end_time")
    def serialize_date(
        self, value: date, _info: FieldSerializationInfo
    ) -> Optional[str]:
        return value.isoformat()
