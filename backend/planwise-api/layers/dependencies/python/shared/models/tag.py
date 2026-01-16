from pydantic import BaseModel, computed_field

class Tag(BaseModel):
    id: str
    user_id: str
    name: str
    background_color: str
    border_color: str
    text_color: str

    @computed_field
    @property
    def PK(self) -> str:
        return f"USER#{self.user_id}"
