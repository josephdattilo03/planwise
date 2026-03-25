from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class Note(BaseModel):
    id: str
    user_id: str
    title: str = ""
    body: str = ""
    color: str = "bg-pink"
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = 380.0
    height: float = 300.0
    links: List[str] = Field(default_factory=list)
    archived: bool = False
    updated_at: str = ""

    # Legacy schema (older items in DynamoDB)
    board_id: Optional[str] = None
    content: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def merge_legacy(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if d.get("content") and not d.get("body"):
                d["body"] = d["content"]
            return d
        return data

    @field_validator("position_x", "position_y", "width", "height", mode="before")
    @classmethod
    def coerce_numbers(cls, v: Any) -> Any:
        if isinstance(v, Decimal):
            return float(v)
        return v

    @computed_field
    @property
    def PK(self) -> str:
        return f"USER#{self.user_id}"

    @computed_field
    @property
    def SK(self) -> str:
        return f"NOTE#{self.id}"
