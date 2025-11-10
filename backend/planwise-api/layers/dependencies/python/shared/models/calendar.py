# Please use pydantic model validation
from pydantic import BaseModel


class Calendar(BaseModel):
    id: str
    name: str
    calendar_color: str
