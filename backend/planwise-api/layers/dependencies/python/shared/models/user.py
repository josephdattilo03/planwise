from pydantic import BaseModel, field_serializer, FieldSerializationInfo
from datetime import date

class User(BaseModel):
    id: str
    name: str
    timezone: str
    created_at: date

    @field_serializer("created_at")
    def serialize_date(self, value: date, _info: FieldSerializationInfo) -> str:
        return value.isoformat()