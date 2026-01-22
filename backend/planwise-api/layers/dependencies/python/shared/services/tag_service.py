from shared.models.tag import Tag
from shared.repositories.tag_repository import TagRepository


class TagService:
    def __init__(self):
        self.repository = TagRepository()

    def create_tag(self, tag: Tag) -> Tag:
        """Create a new tag"""
        tag_dict = tag.model_dump()
        tag_dict["SK"] = f"TAG#{tag.id}"
        self.repository.save(tag_dict)
        return tag

    def get_tag(self, user_id: str, tag_id: str) -> Tag:
        """Get a tag by user_id and tag_id"""
        pk = f"USER#{user_id}"
        sk = f"TAG#{tag_id}"
        tag_data = self.repository.get_by_id_pair(pk, sk)
        return Tag(**tag_data)

    def update_tag(self, tag: Tag) -> Tag:
        """Update an existing tag"""
        tag_dict = tag.model_dump()
        tag_dict["SK"] = f"TAG#{tag.id}"
        self.repository.update_by_id_pair(tag_dict)
        return tag

    def delete_tag(self, user_id: str, tag_id: str) -> None:
        """Delete a tag by user_id and tag_id"""
        pk = f"USER#{user_id}"
        sk = f"TAG#{tag_id}"
        self.repository.delete_by_id_pair(pk, sk)
