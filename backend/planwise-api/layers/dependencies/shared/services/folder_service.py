from shared.repositories.folder_repository import FolderRepository
from shared.models.folder import Folder
from shared.models.board import Board
from typing import Optional, Any, List
from shared.utils.errors import BadRequestError, NotFoundError, ValidationAppError
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
        try:
            existing = self.repository.get_by_id_pair(
                f"USER#{user_id}", f"FOLDER#{self.root_folder_id}"
            )
        except NotFoundError:
            existing = None

        if existing:
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

    def delete_folder_recursive(self, folder_id: str, user_id: str) -> None:
        """Delete folder and all descendant folders; delete boards under this path."""
        if folder_id == self.root_folder_id:
            e = BadRequestError()
            e.message = "Cannot delete root folder"
            raise e
        self.ensure_root_folder(user_id)
        target = self.get_folder_by_id(folder_id, user_id)
        if not target:
            raise NotFoundError()
        from shared.services.board_service import BoardService

        board_svc = BoardService()
        old_prefix = target.path.rstrip("/")

        all_boards = board_svc.get_boards_by_user_id(user_id) or []
        boards_to_delete = [
            b
            for b in all_boards
            if b and b.path.startswith(old_prefix + "/")
        ]

        raw_folders = self.get_boards_by_user_id(user_id) or []
        folders = [f for f in raw_folders if f is not None]
        folders_to_delete = [
            f
            for f in folders
            if f.id != self.root_folder_id
            and (f.id == folder_id or f.path.startswith(old_prefix + "/"))
        ]
        folders_to_delete.sort(key=lambda x: -x.depth)

        for b in boards_to_delete:
            board_svc.delete_board(b.id, user_id)
        for f in folders_to_delete:
            self.repository.delete_by_id_pair(f"USER#{user_id}", f"FOLDER#{f.id}")

    def move_folder(self, user_id: str, folder_id: str, new_parent_id: str) -> Folder:
        """Reparent a folder under new_parent_id; updates all descendant paths and depths."""
        if folder_id == self.root_folder_id:
            e = BadRequestError()
            e.message = "Cannot move root folder"
            raise e
        self.ensure_root_folder(user_id)
        folder = self.get_folder_by_id(folder_id, user_id)
        new_parent = self.get_folder_by_id(new_parent_id, user_id)
        if not folder or not new_parent:
            raise NotFoundError()
        if new_parent_id == folder_id:
            e = BadRequestError()
            e.message = "Invalid parent folder"
            raise e
        old_prefix = folder.path.rstrip("/")
        if new_parent.path.startswith(old_prefix + "/"):
            e = BadRequestError()
            e.message = "Cannot move folder into its descendant"
            raise e

        from shared.services.board_service import BoardService

        board_svc = BoardService()
        last_segment = old_prefix.split("/")[-1]
        new_base = new_parent.path.rstrip("/")
        new_f_path = f"{new_base}/{last_segment}"
        depth_delta = (new_parent.depth + 1) - folder.depth

        all_folders = [f for f in (self.get_boards_by_user_id(user_id) or []) if f]
        all_boards = [b for b in (board_svc.get_boards_by_user_id(user_id) or []) if b]

        for f in all_folders:
            if f.id == self.root_folder_id:
                continue
            if f.path == old_prefix:
                nf = Folder(
                    id=f.id,
                    user_id=user_id,
                    name=f.name,
                    path=new_f_path,
                    depth=f.depth + depth_delta,
                )
                self.update_folder(nf)
            elif f.path.startswith(old_prefix + "/"):
                suffix = f.path[len(old_prefix) :]
                new_path = new_f_path + suffix
                nf = Folder(
                    id=f.id,
                    user_id=user_id,
                    name=f.name,
                    path=new_path,
                    depth=f.depth + depth_delta,
                )
                self.update_folder(nf)

        for b in all_boards:
            if b.path.startswith(old_prefix + "/"):
                suffix = b.path[len(old_prefix) :]
                new_path = new_f_path + suffix
                nb = Board(
                    id=b.id,
                    user_id=user_id,
                    name=b.name,
                    color=b.color,
                    path=new_path,
                    depth=b.depth + depth_delta,
                )
                board_svc.update_board(nb)

        result = self.get_folder_by_id(folder_id, user_id)
        if not result:
            raise NotFoundError()
        return result
    
    def _item_to_folder(self, item: dict[str, Any]) -> Optional[Folder]:
        if not item:
            return None
        try:
            folder = Folder(**item)
            return folder  # Fixed: return instead of raise
        except ValidationError as e:
            raise ValidationAppError(e.errors())