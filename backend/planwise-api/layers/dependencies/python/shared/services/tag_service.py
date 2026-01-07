from shared.repositories.tag_repository import TagRepository

class TagService:
    def __init__(self):
        self.repository = TagRepository()