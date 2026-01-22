from shared.utils.db import get_table
from shared.repositories.repository import Repository


class UserRepository(Repository):
    def __init__(self):
        self.table = get_table("user-table")