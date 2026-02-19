from shared.repositories.note_repository import NoteRepository
from shared.models.note import Note
from typing import Any
from pydantic import ValidationError
from shared.utils.errors import ValidationAppError


class NoteService:
    def __init__(self):
        self.repository = NoteRepository()

    def create_note(self, note: Note) -> Note:
        note_dict = note.model_dump()
        self.repository.save(note_dict)
        return note

    def get_note_by_id(self, note_id: str, user_id: str) -> Note:
        item = self.repository.get_by_id_pair(f"USER#{user_id}", f"NOTE#{note_id}")
        return self._item_to_note(item)

    def update_note(self, note: Note) -> Note:
        note_dict = note.model_dump()
        self.repository.update_by_id_pair(note_dict)
        return note

    def delete_note(self, note_id: str, user_id: str) -> None:
        self.repository.delete_by_id_pair(f"USER#{user_id}", f"NOTE#{note_id}")

    def _item_to_note(self, item: dict[str, Any]) -> Note:
        if not item:
            raise ValidationAppError([])
        try:
            return Note(**item)
        except ValidationError as e:
            raise ValidationAppError(e.errors())