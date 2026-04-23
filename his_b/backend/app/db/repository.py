"""
Repository: queries HIS B legacy tables and maps rows to FHIR R5 dicts.

Mapping conventions
-------------------
- Patient     ← patients table
- Observation ← observations table
- ServiceRequest ← service_requests table
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.db.database import get_pool

# ---------------------------------------------------------------------------
# Private helpers: legacy row → FHIR dict
# ---------------------------------------------------------------------------

_GENDER_MAP = {"M": "male", "F": "female", "U": "unknown"}


def _patient_to_fhir(row: Any) -> dict:
    gender = _GENDER_MAP.get(row["gender"] or "U", "unknown")
    resource: dict = {
        "resourceType": "Patient",
        "id": row["hn"],
        "identifier": [
            {"system": "urn:his-b:hn", "value": row["hn"]}
        ],
        "name": [
            {
                "family": row["last_name"],
                "given": [row["first_name"]],
            }
        ],
        "gender": gender,
    }
    if row["dob"]:
        resource["birthDate"] = row["dob"].isoformat()
    if row["phone"]:
        resource["telecom"] = [{"system": "phone", "value": row["phone"]}]
    if row["address"]:
        resource["address"] = [{"text": row["address"]}]
    if row["id_card"]:
        resource["identifier"].append(
            {"system": "urn:th:national-id", "value": row["id_card"]}
        )
    return resource


def _observation_to_fhir(row: Any) -> dict:
    resource: dict = {
        "resourceType": "Observation",
        "id": str(row["id"]),
        "status": row["status"] or "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": row["loinc_code"],
                    "display": row["display"],
                }
            ]
        },
        "subject": {"reference": f"Patient/{row['patient_hn']}"},
        "issued": row["issued_at"].isoformat(),
    }
    # Attempt numeric cast; fall back to valueString
    try:
        resource["valueQuantity"] = {
            "value": float(row["value"]),
            "unit": row["unit"],
            "system": "http://unitsofmeasure.org",
            "code": row["unit"],
        }
    except (TypeError, ValueError):
        if row["value"]:
            resource["valueString"] = row["value"]
    return resource


def _service_request_to_fhir(row: Any) -> dict:
    return {
        "resourceType": "ServiceRequest",
        "id": str(row["id"]),
        "status": row["status"] or "active",
        "intent": "order",
        "priority": row["priority"] or "routine",
        "code": {
            "coding": [
                {
                    "system": "urn:his-b:order-codes",
                    "code": row["order_code"],
                    "display": row["display"],
                }
            ]
        },
        "subject": {"reference": f"Patient/{row['patient_hn']}"},
        "authoredOn": row["requested_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# Public repository functions
# ---------------------------------------------------------------------------


async def list_patients() -> list[dict]:
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM patients ORDER BY created_at DESC"
    )
    return [_patient_to_fhir(r) for r in rows]


async def get_patient(hn: str) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM patients WHERE hn = $1", hn)
    return _patient_to_fhir(row) if row else None


async def create_patient(data: dict) -> dict:
    """Store a new patient from a FHIR Patient resource."""
    pool = get_pool()
    hn = data.get("id") or _extract_identifier(data, "urn:his-b:hn")
    name = (data.get("name") or [{}])[0]
    first_name = (name.get("given") or [""])[0]
    last_name = name.get("family", "")
    gender = {"male": "M", "female": "F"}.get(data.get("gender", ""), "U")
    dob_raw = data.get("birthDate")
    dob = date.fromisoformat(dob_raw) if isinstance(dob_raw, str) else dob_raw
    phone = _extract_telecom(data, "phone")
    address_list = data.get("address") or []
    address = address_list[0].get("text") if address_list else None
    id_card = _extract_identifier(data, "urn:th:national-id")

    row = await pool.fetchrow(
        """
        INSERT INTO patients (hn, first_name, last_name, gender, dob, phone, address, id_card)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (hn) DO UPDATE
          SET first_name=$2, last_name=$3, gender=$4, dob=$5, phone=$6, address=$7, id_card=$8
        RETURNING *
        """,
        hn, first_name, last_name, gender, dob, phone, address, id_card,
    )
    return _patient_to_fhir(row)


def _extract_identifier(data: dict, system: str) -> Optional[str]:
    for ident in data.get("identifier") or []:
        if ident.get("system") == system:
            return ident.get("value")
    return None


def _extract_telecom(data: dict, system: str) -> Optional[str]:
    for t in data.get("telecom") or []:
        if t.get("system") == system:
            return t.get("value")
    return None


async def list_observations(patient_hn: Optional[str] = None) -> list[dict]:
    pool = get_pool()
    if patient_hn:
        rows = await pool.fetch(
            "SELECT * FROM observations WHERE patient_hn = $1 ORDER BY issued_at DESC",
            patient_hn,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM observations ORDER BY issued_at DESC"
        )
    return [_observation_to_fhir(r) for r in rows]


async def get_observation(obs_id: int) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM observations WHERE id = $1", obs_id)
    return _observation_to_fhir(row) if row else None


async def list_service_requests(patient_hn: Optional[str] = None) -> list[dict]:
    pool = get_pool()
    if patient_hn:
        rows = await pool.fetch(
            "SELECT * FROM service_requests WHERE patient_hn = $1 ORDER BY requested_at DESC",
            patient_hn,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM service_requests ORDER BY requested_at DESC"
        )
    return [_service_request_to_fhir(r) for r in rows]


async def get_service_request(sr_id: int) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM service_requests WHERE id = $1", sr_id)
    return _service_request_to_fhir(row) if row else None


# ---------------------------------------------------------------------------
# Patient – update / delete
# ---------------------------------------------------------------------------


async def update_patient(hn: str, data: dict) -> Optional[dict]:
    """Update an existing patient from a FHIR Patient resource."""
    pool = get_pool()
    name = (data.get("name") or [{}])[0]
    first_name = (name.get("given") or [""])[0]
    last_name = name.get("family", "")
    gender = {"male": "M", "female": "F"}.get(data.get("gender", ""), "U")
    dob_raw = data.get("birthDate")
    dob = date.fromisoformat(dob_raw) if isinstance(dob_raw, str) else dob_raw
    phone = _extract_telecom(data, "phone")
    address_list = data.get("address") or []
    address = address_list[0].get("text") if address_list else None
    id_card = _extract_identifier(data, "urn:th:national-id")

    row = await pool.fetchrow(
        """
        UPDATE patients
        SET first_name=$2, last_name=$3, gender=$4, dob=$5, phone=$6, address=$7, id_card=$8
        WHERE hn=$1
        RETURNING *
        """,
        hn, first_name, last_name, gender, dob, phone, address, id_card,
    )
    return _patient_to_fhir(row) if row else None


async def delete_patient(hn: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as con:
        async with con.transaction():
            await con.execute("DELETE FROM service_requests WHERE patient_hn = $1", hn)
            await con.execute("DELETE FROM observations WHERE patient_hn = $1", hn)
            result = await con.execute("DELETE FROM patients WHERE hn = $1", hn)
    return result != "DELETE 0"


# ---------------------------------------------------------------------------
# Observation – create / update / delete
# ---------------------------------------------------------------------------


async def create_observation(data: dict) -> dict:
    """Store a new observation from a FHIR Observation resource."""
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    if not patient_hn:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="subject.reference (Patient HN) is required.")

    # Verify patient exists
    exists = await pool.fetchval("SELECT hn FROM patients WHERE hn = $1", patient_hn)
    if not exists:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Patient {patient_hn!r} not found.")

    coding = ((data.get("code") or {}).get("coding") or [{}])[0]
    loinc_code = coding.get("code", "")
    display = coding.get("display", "")
    status_ = data.get("status", "final")

    vq = data.get("valueQuantity") or {}
    value = str(vq.get("value", "")) if vq else (data.get("valueString") or "")
    unit = vq.get("unit", "") if vq else ""

    row = await pool.fetchrow(
        """
        INSERT INTO observations (patient_hn, loinc_code, display, value, unit, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        patient_hn, loinc_code, display, value, unit, status_,
    )
    return _observation_to_fhir(row)


async def update_observation(obs_id: int, data: dict) -> Optional[dict]:
    """Update an existing observation from a FHIR Observation resource."""
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    coding = ((data.get("code") or {}).get("coding") or [{}])[0]
    loinc_code = coding.get("code", "")
    display = coding.get("display", "")
    status_ = data.get("status", "final")

    vq = data.get("valueQuantity") or {}
    value = str(vq.get("value", "")) if vq else (data.get("valueString") or "")
    unit = vq.get("unit", "") if vq else ""

    row = await pool.fetchrow(
        """
        UPDATE observations
        SET patient_hn=$2, loinc_code=$3, display=$4, value=$5, unit=$6, status=$7
        WHERE id=$1
        RETURNING *
        """,
        obs_id, patient_hn, loinc_code, display, value, unit, status_,
    )
    return _observation_to_fhir(row) if row else None


async def delete_observation(obs_id: int) -> bool:
    pool = get_pool()
    result = await pool.execute("DELETE FROM observations WHERE id = $1", obs_id)
    # asyncpg returns e.g. "DELETE 1" or "DELETE 0"
    return result != "DELETE 0"


# ---------------------------------------------------------------------------
# ServiceRequest – create / update / delete
# ---------------------------------------------------------------------------


async def create_service_request(data: dict) -> dict:
    """Store a new service request from a FHIR ServiceRequest resource."""
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    if not patient_hn:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="subject.reference (Patient HN) is required.")

    # Verify patient exists
    exists = await pool.fetchval("SELECT hn FROM patients WHERE hn = $1", patient_hn)
    if not exists:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Patient {patient_hn!r} not found.")

    coding = ((data.get("code") or {}).get("coding") or [{}])[0]
    order_code = coding.get("code", "")
    display = coding.get("display", "")
    priority = data.get("priority", "routine")
    status_ = data.get("status", "active")

    row = await pool.fetchrow(
        """
        INSERT INTO service_requests (patient_hn, order_code, display, priority, status)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        patient_hn, order_code, display, priority, status_,
    )
    return _service_request_to_fhir(row)


async def update_service_request(sr_id: int, data: dict) -> Optional[dict]:
    """Update an existing service request from a FHIR ServiceRequest resource."""
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    coding = ((data.get("code") or {}).get("coding") or [{}])[0]
    order_code = coding.get("code", "")
    display = coding.get("display", "")
    priority = data.get("priority", "routine")
    status_ = data.get("status", "active")

    row = await pool.fetchrow(
        """
        UPDATE service_requests
        SET patient_hn=$2, order_code=$3, display=$4, priority=$5, status=$6
        WHERE id=$1
        RETURNING *
        """,
        sr_id, patient_hn, order_code, display, priority, status_,
    )
    return _service_request_to_fhir(row) if row else None


async def delete_service_request(sr_id: int) -> bool:
    pool = get_pool()
    result = await pool.execute("DELETE FROM service_requests WHERE id = $1", sr_id)
    return result != "DELETE 0"
