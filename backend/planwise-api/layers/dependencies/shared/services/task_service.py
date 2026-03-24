from shared.models.task import Task
from shared.repositories.task_repository import TaskRepository
from typing import Any
from pydantic import ValidationError
from shared.utils.errors import ValidationAppError


class TaskService:
    def __init__(self):
        self.repository = TaskRepository()
        self.gsi1_index = "GSI1"
        self.gsi1_pk = "GSI1PK"

    def create_task(self, task: Task) -> Task:
        """Create a new task"""
        task_dict = task.model_dump()
        task_dict["SK"] = f"TASK#{task.id}"
        self.repository.save(task_dict)
        return task

    def get_task(self, board_id: str, task_id: str) -> Task:
        """Get a task by board_id and task_id"""
        pk = f"BOARD#{board_id}"
        sk = f"TASK#{task_id}"
        task_data = self.repository.get_by_id_pair(pk, sk)
        return Task(**task_data)
    
    def get_tasks_by_user_id(self, user_id: str):
        items = self.repository.query_with_sort_key(
        f"USER#{user_id}",
        pk_attr=self.gsi1_pk,
        index_name=self.gsi1_index
        )
        return [self._item_to_task(item) for item in items]

        

    def update_task(self, task: Task) -> Task:
        """Update an existing task"""
        task_dict = task.model_dump()
        task_dict["SK"] = f"TASK#{task.id}"
        self.repository.update_by_id_pair(task_dict)
        return task

    def delete_task(self, board_id: str, task_id: str) -> None:
        """Delete a task by board_id and task_id"""
        pk = f"BOARD#{board_id}"
        sk = f"TASK#{task_id}"
        self.repository.delete_by_id_pair(pk, sk)

    def _item_to_task(self, item: dict[str, Any]):
        try:
            task = Task(**item)
        except ValidationError as e:
            raise ValidationAppError(e.errors())
        return task
