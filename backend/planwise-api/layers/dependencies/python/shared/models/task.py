from pydantic import BaseModel, field_serializer, computed_field, FieldSerializationInfo
from typing import Literal
from datetime import date

class Task(BaseModel):
    id: str
    board_id: str
    name: str
    description: str
    progress: Literal["to-do", "in-progress", "done", "pending"]
    priority_level: int
    due_date: date
    created_at: date

    @field_serializer("due_date", "created_at")
    def date_serializer(self, value: date, _info: FieldSerializationInfo):
        return value.isoformat()

    @computed_field
    @property
    def PK(self) -> str:
        return f"BOARD#{self.board_id}"

    @computed_field
    @property
    def SK(self) -> str:
        return f"TASK#{self.id}"