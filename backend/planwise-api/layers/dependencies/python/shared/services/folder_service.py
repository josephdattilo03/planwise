from shared.repositories.folder_repository import FolderRepository
from shared.models.folder import Folder
from typing import Optional, Any
from shared.utils.errors import ValidationAppError
from pydantic import ValidationError

class FolderService:
    def __init__(self):
        self.repository = FolderRepository()

    def create_folder(self, folder: Folder) -> Folder:
        folder_dict = folder.model_dump()
        self.repository.save(folder_dict)
        return folder
    def get_folder_by_id(self, folder_id: str, user_id: str) -> Optional[Folder]:
        item = self.repository.get_by_id_pair(f"USER#{user_id}", f"FOLDER{folder_id}")
        return self._item_to_folder(item)
    
    def update_folder(self, folder: Folder) -> Folder:
        folder_dict = folder.model_dump()
        self.repository.update_by_id_pair(folder_dict)
        return folder
    def delete_folder(self, folder_id: str, user_id: str):
        self.repository.delete_by_id_pair(f"USER#{user_id}", f"FOLDER#{folder_id}")
    def _item_to_folder(self, item: dict[str, Any]) -> Folder:
        try:
            folder = Folder(**item)
        except ValidationError as e:
            raise ValidationAppError(e.errors())
        raise folder
        
    