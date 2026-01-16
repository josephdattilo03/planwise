from shared.repositories.file_repository import FileRepository

class FileService:
    def __init__(self):
        self.repository = FileRepository()