from typing import Any, List, Optional, cast

from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import Table
from shared.utils.errors import NotFoundError


class Repository:
    table: Table

    def save(self, save_dict: dict[str, Any]) -> dict[str, Any]:
        self.table.put_item(Item=save_dict)
        return save_dict

    def get_by_id_pair(self, pk: str, sk: str) -> Optional[dict[str, Any]]:
        res = self.table.get_item(Key={"PK": pk, "SK": sk})
        if "Item" not in res:
            raise NotFoundError()
        item = res.get("Item")
        if item is None:
            raise NotFoundError()
        return cast(dict[str, Any], item)

    def delete_by_id_pair(self, pk: str, sk: str) -> None:
        response = self.table.delete_item(
            Key={"PK": pk, "SK": sk}, ReturnValues="ALL_OLD"
        )
        if not response.get("Attributes"):
            raise NotFoundError()

    def get_pk_list(self, pk: str) -> list[dict[str, Any]]:
        response = self.table.query(KeyConditionExpression=Key("PK").eq(pk))
        items = response.get("Items")
        if items is None:
            return []
        return cast(list[dict[str, Any]], items)

    def update_by_id_pair(self, update_object: dict[str, Any]) -> dict[str, Any]:
        self.table.put_item(
            Item=update_object,
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
        )
        return update_object

    def query_with_sort_key(
        self,
        pk: str,
        sk_prefix: Optional[str] = None,
        pk_attr: str = "PK",
        sk_attr: Optional[str] = None,
        index_name: Optional[str] = None
    ) -> List[dict[str, Any]]:

        query_kwargs: dict[str, Any] = {"KeyConditionExpression": Key(pk_attr).eq(pk)}

        if sk_prefix:
            query_kwargs["KeyConditionExpression"] &= Key(sk_attr).begins_with(
                sk_prefix
            )

        if index_name:
            query_kwargs["IndexName"] = index_name

        response = self.table.query(**query_kwargs)
        items = response.get("Items")
        if items is None:
            return []
        return cast(list[dict[str, Any]], items)
