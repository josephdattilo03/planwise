from pydantic import BaseModel, computed_field


class Board(BaseModel):
    id: str
    user_id: str
    depth: int
    path: str
    name: str
    color: str

    
    @computed_field
    @property
    def PK(self) -> str:
        return f"USER#{self.user_id}"

    @computed_field
    @property
    def SK(self) -> str:
        return f"BOARD#{self.id}"
