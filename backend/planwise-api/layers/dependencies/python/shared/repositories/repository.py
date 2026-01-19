from shared.utils.db import get_table
from typing import Any, Optional
from shared.utils.errors import NotFoundError

class Repository:

    def save(self, save_dict: dict[str, Any]) -> dict[str, Any]:
        self.table.put_item(Item=save_dict)
        return save_dict

    def get_by_id_pair(self, pk: str, sk: str) -> Optional[dict[str, Any]]:
        print(f"PK: {pk}")
        print(f"SK: {sk}")
        res = self.table.get_item(Key={
            "PK": pk,
            "SK": sk
        })
        print(res)
        if "Item" not in res:
            raise NotFoundError()
        return res.get("Item")
            
    def delete_by_id_pair(self, pk: str, sk: str):
        response = self.table.delete_item(Key={
            "PK": pk,
            "SK": sk
        },
        ReturnValues="ALL_OLD")
        print(response)
        if not response.get("Attributes"):
            raise NotFoundError()

    def update_by_id_pair(self, update_object: dict[str, Any]) -> dict[str, Any]:
        print("at the repository layer about to insert")
        print(update_object)
        self.table.put_item(
            Item=update_object,
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)"
        )
        return update_object
            
                

