from shared.utils.db import get_table
from typing import Any, Optional, List
from shared.utils.errors import NotFoundError
from boto3.dynamodb.conditions import Key

class Repository:

    def save(self, save_dict: dict[str, Any]) -> dict[str, Any]:
        self.table.put_item(Item=save_dict)
        return save_dict

    def get_by_id_pair(self, pk: str, sk: str) -> Optional[dict[str, Any]]:
        res = self.table.get_item(Key={
            "PK": pk,
            "SK": sk
        })
        if "Item" not in res:
            raise NotFoundError()
        return res.get("Item")
            
    def delete_by_id_pair(self, pk: str, sk: str):
        response = self.table.delete_item(Key={
            "PK": pk,
            "SK": sk
        },
        ReturnValues="ALL_OLD")
        if not response.get("Attributes"):
            raise NotFoundError()
    
    def get_pk_list(self, pk: str) -> Optional[List[dict[str, Any]]]:
        response = self.table.query(
            KeyConditionExpression=Key('PK').eq(pk)
        )
        return response.get('Items', [])

    def update_by_id_pair(self, update_object: dict[str, Any]) -> dict[str, Any]:
        self.table.put_item(
            Item=update_object,
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)"
        )
        return update_object
            
                

