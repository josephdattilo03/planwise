from shared.utils.db import get_table
from shared.repositories.repository import Repository

class FolderRepository(Repository):
    def __init__(self):
        self.table = get_table("folder-table")