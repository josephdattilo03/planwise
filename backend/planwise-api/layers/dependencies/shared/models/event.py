# Please use pydantic model validation
from datetime import date
import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, FieldSerializationInfo, computed_field, field_serializer


class Recurrence(BaseModel):
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    day_of_week: List[
        Literal[
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ]
    ]
    termination_date: date
    date_start: Optional[date] = None

    @field_serializer("termination_date", "date_start")
    def serialize_date(
        self, value: Optional[date], _info: FieldSerializationInfo
    ) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()


class Event(BaseModel):
    id: str
    board_id: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    event_color: str
    is_all_day: bool
    description: str
    location: str
    recurrence: Optional[Recurrence]

    @field_serializer("start_time", "end_time")
    def serialize_date(self, value: date, _info: FieldSerializationInfo) -> str:
        return value.isoformat()

    @computed_field
    def PK(self) -> str:
        return f"BOARD#{self.board_id}"

    @computed_field
    def SK(self) -> str:
        return f"EVENT#{self.id}"
