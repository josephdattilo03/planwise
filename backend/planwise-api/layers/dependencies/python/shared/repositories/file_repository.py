from shared.utils.db import get_table
from repository import Repository

class FileRepository(Repository):
    def __init__(self):
        self.table = get_table("file-table")