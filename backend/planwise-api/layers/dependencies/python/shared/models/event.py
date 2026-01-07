# Please use pydantic model validation
from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, FieldSerializationInfo, field_serializer, computed_field


class Recurrence(BaseModel):
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    day_of_week: List[
        Literal[
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ]
    ]
    termination_date: date
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
    board_id: str
    start_time: date
    end_time: date
    event_color: str
    is_all_day: bool
    description: str
    location: str
    recurrence: Optional[Recurrence]

    @field_serializer("start_time", "end_time")
    def serialize_date(
        self, value: date, _info: FieldSerializationInfo
    ) -> str:
        return value.isoformat()
    
    @computed_field
    @property
    def PK(self) -> str: return f"BOARD#{self.id}"

    @computed_field
    @property
    def SK(self) -> str: return f"EVENT#{self.board_id}"
