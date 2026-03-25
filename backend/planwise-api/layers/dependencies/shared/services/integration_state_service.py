"""Persist per-user integration fingerprints (e.g. Canvas assignment snapshot)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from botocore.exceptions import ClientError

from shared.utils.db import get_table

CANVAS_SK = "canvas_assignments"


class IntegrationStateService:
    def __init__(self, table_name: Optional[str] = None) -> None:
        name = table_name or os.environ.get("INTEGRATION_STATE_TABLE", "")
        if not name:
            raise RuntimeError("INTEGRATION_STATE_TABLE is not set")
        self._table = get_table(name)

    def get_canvas_fingerprint(self, user_id: str) -> Optional[str]:
        fp, _ = self.get_canvas_state(user_id)
        return fp

    def get_canvas_state(
        self, user_id: str
    ) -> tuple[Optional[str], Optional[list[Any]]]:
        try:
            res = self._table.get_item(
                Key={"PK": user_id, "SK": CANVAS_SK},
                ProjectionExpression="fingerprint, #d",
                ExpressionAttributeNames={"#d": "digest"},
            )
        except ClientError:
            return None, None
        item = res.get("Item") or {}
        fp = item.get("fingerprint")
        fp_s = str(fp) if fp else None
        raw = item.get("digest")
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return fp_s, parsed
            except json.JSONDecodeError:
                pass
        return fp_s, None

    def put_canvas_state(
        self, user_id: str, fingerprint: str, digest: list[Any]
    ) -> None:
        self._table.put_item(
            Item={
                "PK": user_id,
                "SK": CANVAS_SK,
                "fingerprint": fingerprint,
                "digest": json.dumps(digest),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
