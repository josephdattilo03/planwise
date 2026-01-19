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
        return f"USER#{self.user_id}"
    
    @computed_field
    @property
    def SK(self) -> str:
        return f"FOLDER#{self.id}"

    @computed_field
    @property
    def GSI1PK(self) -> str:
        return f"#USER#{self.user_id}"
    
    @computed_field
    @property
    def GSI1SK(self) -> str:
        return f"#DEPTH#{self.depth}#PATH#{self.path}"