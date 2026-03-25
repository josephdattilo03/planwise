"""Persist per-user integration fingerprints (e.g. Canvas assignment snapshot)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

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
        try:
            res = self._table.get_item(
                Key={"PK": user_id, "SK": CANVAS_SK},
                ProjectionExpression="fingerprint",
            )
        except ClientError:
            return None
        item = res.get("Item") or {}
        fp = item.get("fingerprint")
        return str(fp) if fp else None

    def put_canvas_fingerprint(self, user_id: str, fingerprint: str) -> None:
        self._table.put_item(
            Item={
                "PK": user_id,
                "SK": CANVAS_SK,
                "fingerprint": fingerprint,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
