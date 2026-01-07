from pydantic import BaseModel, computed_field

class Folder(BaseModel):
    id: str
    user_id: str
    path: str
    depth: int
    name: str
    
    @computed_field
    @property
    def PK(self) -> str:
        return f"#USER#{self.user_id}"
    
    @computed_field
    @property
    def SK(self) -> str:
        return f"PATH#{self.depth}#{self.path}"