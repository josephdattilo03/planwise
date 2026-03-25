from decimal import Decimal
from typing import Any, List

from pydantic import ValidationError

from shared.models.note import Note
from shared.repositories.note_repository import NoteRepository
from shared.utils.errors import ValidationAppError


def _normalize_dynamo_numbers(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in item.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out


def _floats_to_decimal(obj: Any) -> Any:
    """DynamoDB via boto3 does not accept Python float; use Decimal."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimal(v) for v in obj]
    return obj


class NoteService:
    def __init__(self):
        self.repository = NoteRepository()

    def create_note(self, note: Note) -> Note:
        note_dict = _floats_to_decimal(note.model_dump())
        self.repository.save(note_dict)
        return note

    def get_note_by_id(self, note_id: str, user_id: str) -> Note:
        item = self.repository.get_by_id_pair(f"USER#{user_id}", f"NOTE#{note_id}")
        return self._item_to_note(item)

    def get_notes_by_user_id(self, user_id: str) -> List[Note]:
        items = self.repository.get_pk_list(f"USER#{user_id}")
        notes: List[Note] = []
        for item in items:
            sk = item.get("SK", "")
            if not str(sk).startswith("NOTE#"):
                continue
            notes.append(self._item_to_note(item))
        notes.sort(key=lambda n: n.updated_at or "", reverse=True)
        return notes

    def update_note(self, note: Note) -> Note:
        note_dict = _floats_to_decimal(note.model_dump())
        self.repository.update_by_id_pair(note_dict)
        return note

    def delete_note(self, note_id: str, user_id: str) -> None:
        self.repository.delete_by_id_pair(f"USER#{user_id}", f"NOTE#{note_id}")

    def _item_to_note(self, item: dict[str, Any]) -> Note:
        if not item:
            raise ValidationAppError([])
        normalized = _normalize_dynamo_numbers(item)
        try:
            return Note(**normalized)
        except ValidationError as e:
            raise ValidationAppError(e.errors())
