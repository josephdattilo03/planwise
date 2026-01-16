from shared.utils.db import get_table
from repository import Repository


class UserRepository(Repository):
    def __init__(self):
        self.table = get_table("user-table")