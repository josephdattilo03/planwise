from shared.repositories.task_repository import TaskRepository

class TaskService:
    def __init__(self):
        self.repository = TaskRepository()