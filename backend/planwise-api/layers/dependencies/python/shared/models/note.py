from pydantic import BaseModel, computed_field

class Note(BaseModel):
    id: str
    user_id: str
    board_id: str
    content: str

    @computed_field
    @property
    def PK(self) -> str:
        return f"USER#{self.user_id}"

    @computed_field
    @property
    def SK(self) -> str:
        return f"NOTE#{self.id}"
