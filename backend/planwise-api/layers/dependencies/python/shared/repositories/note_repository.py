from repository import Repository
from shared.repositories.repository import get_table

class NoteRepository(Repository):
    def __init__(self):
        self.table = get_table("note-table")