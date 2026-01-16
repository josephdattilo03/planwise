from shared.utils.db import get_table
from shared.repositories.repository import Repository

class EventRepository (Repository):

    def __init__(self) -> None:
        self.table = get_table("event-table")

