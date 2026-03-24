from datetime import date
from typing import Optional

from pydantic import BaseModel, FieldSerializationInfo, computed_field, field_serializer


class User(BaseModel):
    id: str
    name: str
    timezone: str
    created_at: date

    # Google OAuth fields
    google_access_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    google_token_expiry: Optional[int] = None  # Seconds until token expires

    @field_serializer("created_at")
    def serialize_date(self, value: date, _info: FieldSerializationInfo) -> str:
        return value.isoformat()

    @field_serializer("google_access_token", "google_refresh_token")
    def serialize_google_token(
        self, value: Optional[str], _info: FieldSerializationInfo
    ) -> Optional[str]:
        return value

    @field_serializer("google_token_expiry")
    def serialize_google_token_expiry(
        self, value: Optional[int], _info: FieldSerializationInfo
    ) -> Optional[int]:
        return value

    @computed_field
    def PK(self) -> str:
        return f"USER#{self.id}"

    @computed_field
    def SK(self) -> str:
        return f"USER#{self.id}"
