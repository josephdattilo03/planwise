from shared.repositories.repository import Repository
from shared.utils.db import get_table


class NoteRepository(Repository):
    def __init__(self):
        self.table = get_table("note-table")