# Please use pydantic model validation
from datetime import date
from typing import List, Literal, Optional, Self

from pydantic import (
    BaseModel,
    FieldSerializationInfo,
    field_serializer,
    model_validator,
)


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
    calendar_bucket: Optional[str] = None
    calendar_id: str
    start_time: date
    end_time: date
    event_color: str
    is_all_day: bool
    description: str
    location: str
    timezone: str
    recurrence: Optional[Recurrence]

    @model_validator(mode="after")
    def create_calendar_bucket(self) -> Self:
        if self.calendar_bucket is not None:
            return self

        if self.calendar_id is None or self.start_time is None:
            raise ValueError("Missing calendar_id and start_time")

        yyyy_mm = self.start_time.strftime("%Y_%m")
        print(yyyy_mm)

        self.calendar_bucket = f"{self.calendar_id}#{yyyy_mm}"
        return self

    @field_serializer("start_time", "end_time")
    def serialize_date(
        self, value: date, _info: FieldSerializationInfo
    ) -> Optional[str]:
        return value.isoformat()
