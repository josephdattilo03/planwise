from shared.models.task import Task
from shared.repositories.task_repository import TaskRepository


class TaskService:
    def __init__(self):
        self.repository = TaskRepository()

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
