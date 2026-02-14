from shared.repositories.board_repository import BoardRepository
from shared.models.board import Board
from typing import Optional, Any, List
from pydantic import ValidationError
from shared.utils.errors import ValidationAppError

class BoardService:
    def __init__(self):
        self.repository = BoardRepository()
        self.gsi1_index = "GSI1"
        self.gsi1_pk = "GSI1PK"
        self.gsi1_sk = "GSI1SK"
        
    def create_board(self, board: Board) -> Board:
        board_dict = board.model_dump()
        self.repository.save(board_dict)
        return board
    def get_board_by_id(self, board_id: str, user_id: str) -> Optional[Board]:
        item = self.repository.get_by_id_pair(f"USER#{user_id}", f"BOARD#{board_id}")
        return self._item_to_board(item)
    def get_boards_by_user_id(self, user_id: str) -> Optional[List[Board]]:
        items = self.repository.get_pk_list(f"USER#{user_id}")
        return [self._item_to_board(item) for item in items]
    def update_board(self, board: Board) -> Board:
        board_dict = board.model_dump()
        self.repository.update_by_id_pair(board_dict)
        return board

    def delete_board(self, board_id: str, user_id: str):
        self.repository.delete_by_id_pair(f"USER#{user_id}", f"BOARD#{board_id}")

    def get_boards_at_depth(self, user_id: str, depth: int, path: str):
        items = self.repository.query_with_sort_key(
            f"USER#{user_id}", 
            f"DEPTH#{depth}#PATH#/{path}", 
            self.gsi1_pk, 
            self.gsi1_sk, 
            self.gsi1_index
        )
        return [self._item_to_board(item) for item in items]

    def _item_to_board(self, item: dict[str, Any]):
        try:
            board = Board(**item)
        except ValidationError as e:
            raise ValidationAppError(e.errors())
        return board