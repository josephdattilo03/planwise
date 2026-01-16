from pydantic import BaseModel, computed_field, field_serializer, FieldSerializationInfo
from datetime import date


class Board(BaseModel):
    id: str
    user_id: str
    depth: int
    path: str
    name: str
    color: str
    created_at: date

    
    @computed_field
    @property
    def PK(self) -> str:
        return f"USER#{self.user_id}"

    @computed_field
    @property
    def SK(self) -> str:
        return f"PATH#{self.depth}#{self.path}"

    @field_serializer("created_at")
    def serialize_date(
        self, value: date, _info: FieldSerializationInfo
    ) -> str:
        return value.isoformat()