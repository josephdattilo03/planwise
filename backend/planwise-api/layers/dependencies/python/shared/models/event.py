# Please use pydantic model validation
from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    BaseModel,
    FieldSerializationInfo,
    field_serializer,
    field_validator,
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
    calendar_bucket: str | None = None
    calendar_id: str
    start_time: date
    end_time: date
    event_color: str
    is_all_day: bool
    description: str
    location: str
    timezone: str
    recurrence: Optional[Recurrence]

    @field_validator("calendar_bucket", mode="before")
    def create_calendar_bucket(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if v:
            return v
        calendar_id = values.get("calendar_id")
        start_time = values.get("start_time")
        if calendar_id is None or start_time is None:
            raise ValueError("Missing calendar_id and start_time")
        start_time = date.fromisoformat(start_time)
        yyyy_mm = start_time.strftime("%Y_%m")
        return f"{calendar_id}#{yyyy_mm}"

    @field_serializer("start_time", "end_time")
    def serialize_date(
        self, value: date, _info: FieldSerializationInfo
    ) -> Optional[str]:
        return value.isoformat()
