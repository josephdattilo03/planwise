from shared.utils.db import get_table
from repository import Repository

class BoardRepository(Repository):
    def __init__(self):
        self.repository = get_table("board-table")