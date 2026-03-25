from shared.repositories.repository import Repository
from shared.utils.db import get_table


class UserRepository(Repository):
    def __init__(self) -> None:
        self.table = get_table("user-table")
