from shared.utils.db import get_table
from repository import Repository

class EventRepository (Repository):

    def __init__(self) -> None:
        self.table = get_table("events-table")

