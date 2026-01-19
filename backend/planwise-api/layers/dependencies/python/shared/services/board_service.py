from shared.repositories.board_repository import BoardRepository
from shared.models.board import Board
from typing import Optional, Any
from pydantic import ValidationError
from shared.utils.errors import ValidationAppError

class BoardService:
    def __init__(self):
        self.repository = BoardRepository()
        
    def create_board(self, board: Board) -> Board:
        board_dict = board.model_dump()

        self.repository.save(board_dict)
        return board
    def get_board_by_id(self, board_id: str, user_id: str) -> Optional[Board]:
        item = self.repository.get_by_id_pair(f"USER#{user_id}", f"BOARD#{board_id}")
        return self._item_to_board(item)
    
    def update_board(self, board: Board) -> Board:
        board_dict = board.model_dump()
        self.repository.update_by_id_pair(board_dict)
        return board

    def delete_board(self, board_id: str, user_id: str):
        self.repository.delete_by_id_pair(f"USER#{user_id}", f"BOARD#{board_id}")

    def _item_to_board(self, item: dict[str, Any]):
        try:
            board = Board(**item)
        except ValidationError as e:
            raise ValidationAppError(e.errors())
        return board