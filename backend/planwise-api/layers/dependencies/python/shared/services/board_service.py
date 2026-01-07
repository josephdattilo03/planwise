from shared.repositories.board_repository import BoardRepository

class BoardService:
    def __init__(self):
        self.repository = BoardRepository()