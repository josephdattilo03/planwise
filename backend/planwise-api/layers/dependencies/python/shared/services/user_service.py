from shared.repositories.user_repository import UserRepository

class UserService:
    def __init__(self):
        self.repository = UserRepository()