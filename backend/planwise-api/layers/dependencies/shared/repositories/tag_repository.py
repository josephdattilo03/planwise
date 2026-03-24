from shared.repositories.repository import Repository
from shared.utils.db import get_table

class TagRepository(Repository):
    def __init__(self):
        self.table = get_table("tag-table")