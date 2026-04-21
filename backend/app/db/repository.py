import uuid
from typing import Any, Optional

import asyncpg

from app.db.database import get_pool


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "resource_type": row["resource_type"],
        "patient_id": row["patient_id"],
        "data": row["data"],  # decoded to dict by the JSONB codec
        "created_at": row["created_at"].isoformat(),
    }


async def create_resource(
    resource_type: str, patient_id: Optional[str], data: dict[str, Any]
) -> dict[str, Any]:
    pool = get_pool()
    new_id = uuid.uuid4()
    data["id"] = str(new_id)  # server assigns the FHIR resource id
    row = await pool.fetchrow(
        """
        INSERT INTO fhir_resources (id, resource_type, patient_id, data)
        VALUES ($1, $2, $3, $4)
        RETURNING id, resource_type, patient_id, data, created_at
        """,
        new_id,
        resource_type,
        patient_id,
        data,
    )
    return _row_to_dict(row)


async def get_resource(
    resource_type: str, resource_id: str
) -> Optional[dict[str, Any]]:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, resource_type, patient_id, data, created_at
        FROM fhir_resources
        WHERE id = $1 AND resource_type = $2
        """,
        uuid.UUID(resource_id),
        resource_type,
    )
    return _row_to_dict(row) if row else None


async def update_resource(
    resource_type: str,
    resource_id: str,
    patient_id: Optional[str],
    data: dict[str, Any],
) -> Optional[dict[str, Any]]:
    pool = get_pool()
    data["id"] = resource_id  # keep id consistent with the DB record
    row = await pool.fetchrow(
        """
        UPDATE fhir_resources
        SET patient_id = $3, data = $4
        WHERE id = $1 AND resource_type = $2
        RETURNING id, resource_type, patient_id, data, created_at
        """,
        uuid.UUID(resource_id),
        resource_type,
        patient_id,
        data,
    )
    return _row_to_dict(row) if row else None


async def delete_resource(resource_type: str, resource_id: str) -> bool:
    pool = get_pool()
    result = await pool.execute(
        "DELETE FROM fhir_resources WHERE id = $1 AND resource_type = $2",
        uuid.UUID(resource_id),
        resource_type,
    )
    return result == "DELETE 1"


async def list_resources(resource_type: str) -> list[dict[str, Any]]:
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT id, resource_type, patient_id, data, created_at
        FROM fhir_resources
        WHERE resource_type = $1
        ORDER BY created_at DESC
        """,
        resource_type,
    )
    return [_row_to_dict(r) for r in rows]
