# Please use pydantic model validation
from pydantic import BaseModel
from datetime import date
from typing import Literal, List, Optional

class Recurrence(BaseModel):
    frequency : Literal["daily", "weekly", "monthly", "yearly"]
    day_of_week : List[Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]]
    date_until : date
    date_start : Optional[date] = None

class Event(BaseModel):
    id : int
    calendar_id : int
    start_time : date
    end_time : date
    event_color: str
    is_all_day: bool
    description: str
    location: str
    timezone: str
    recurrence : Optional[Recurrence]