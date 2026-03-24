from typing import Any, List

from pydantic import ValidationError
from shared.models.user import User
from shared.repositories.user_repository import UserRepository
from shared.utils.errors import NotFoundError, ValidationAppError


class UserService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    def create_user(self, user: User) -> User:
        user_dict = user.model_dump()
        self.repository.save(user_dict)
        return user

    def get_user_by_id(self, user_id: str) -> User:
        try:
            item = self.repository.get_by_id_pair(f"USER#{user_id}", f"USER#{user_id}")
            if item is None:
                raise NotFoundError(f"User with id {user_id} not found")
            return self._item_to_user(item)
        except NotFoundError:
            raise NotFoundError(f"User with id {user_id} not found")

    def get_users(self) -> List[User]:
        items = self.repository.get_pk_list("USER")
        return [self._item_to_user(item) for item in items]

    def update_user(self, user: User) -> User:
        user_dict = user.model_dump()
        self.repository.update_by_id_pair(user_dict)
        return user

    def delete_user(self, user_id: str) -> None:
        self.repository.delete_by_id_pair(f"USER#{user_id}", f"USER#{user_id}")

    def _item_to_user(self, item: dict[str, Any]) -> User:
        try:
            user = User(**item)
        except ValidationError as e:
            raise ValidationAppError(e.errors())
        return user
