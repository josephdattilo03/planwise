from shared.utils.db import get_table
from shared.repositories.repository import Repository

class BoardRepository(Repository):
    def __init__(self):
        self.table = get_table("board-table")