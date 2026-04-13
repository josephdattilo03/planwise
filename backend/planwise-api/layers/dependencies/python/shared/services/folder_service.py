from shared.repositories.folder_repository import FolderRepository
from shared.models.folder import Folder
from typing import Optional, Any, List
from shared.utils.errors import ValidationAppError
from pydantic import ValidationError

class FolderService:
    def __init__(self):
        self.repository = FolderRepository()
        self.gsi1_index = "GSI1"
        self.gsi1_pk = "GSI1PK"
        self.gsi1_sk = "GSI1SK"
        self.root_folder_id = "root"
        self.root_folder_name = "Root"
        self.root_folder_path = "/root"
        self.root_folder_depth = 0
    
    def ensure_root_folder(self, user_id: str) -> Folder:
        existing = self.repository.get_by_id_pair(
            f"USER#{user_id}", f"FOLDER#{self.root_folder_id}"
        )
        root = self._item_to_folder(existing)
        if root:
            return root

        root = Folder(
            id=self.root_folder_id,
            user_id=user_id,
            path=self.root_folder_path,
            depth=self.root_folder_depth,
            name=self.root_folder_name,
        )
        self.repository.save(root.model_dump())
        return root
        
    def create_folder(self, folder: Folder) -> Folder:
        folder_dict = folder.model_dump()
        self.repository.save(folder_dict)
        return folder
    
    def get_folder_by_id(self, folder_id: str, user_id: str) -> Optional[Folder]:
        if folder_id == self.root_folder_id:
            self.ensure_root_folder(user_id)
        item = self.repository.get_by_id_pair(f"USER#{user_id}", f"FOLDER#{folder_id}")
        return self._item_to_folder(item)
    
    def get_boards_by_user_id(self, user_id: str) -> Optional[List[Folder]]:
        items = self.repository.get_pk_list(f"USER#{user_id}")
        return [self._item_to_folder(folder) for folder in items]
    
    def get_folders_at_depth(self, user_id: str, depth: int, path: str):
        self.ensure_root_folder(user_id)
        items = self.repository.query_with_sort_key(
            f"USER#{user_id}", 
            f"DEPTH#{depth}#PATH#/{path}", 
            self.gsi1_pk, 
            self.gsi1_sk, 
            self.gsi1_index
        )
        return [self._item_to_folder(item) for item in items]
    
    def update_folder(self, folder: Folder) -> Folder:
        folder_dict = folder.model_dump()
        self.repository.update_by_id_pair(folder_dict)
        return folder
    
    def delete_folder(self, folder_id: str, user_id: str):
        self.repository.delete_by_id_pair(f"USER#{user_id}", f"FOLDER#{folder_id}")
    
    def _item_to_folder(self, item: dict[str, Any]) -> Optional[Folder]:
        if not item:
            return None
        try:
            folder = Folder(**item)
            return folder  # Fixed: return instead of raise
        except ValidationError as e:
            raise ValidationAppError(e.errors())