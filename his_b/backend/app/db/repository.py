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


# ---------------------------------------------------------------------------
# Encounter – helpers + CRUD
# ---------------------------------------------------------------------------

def _encounter_to_fhir(row: Any) -> dict:
    # FHIR R5: class is List[CodeableConcept], period renamed to actualPeriod,
    # reason uses value[].concept structure (EncounterReason.value = CodeableReference[])
    # PostgreSQL returns naive datetimes — append +07:00 so FHIR DateTime regex passes
    def _dt(ts: Any) -> str:
        s = ts.isoformat()
        if s and '+' not in s and 'Z' not in s:
            s += '+07:00'
        return s

    resource: dict = {
        "resourceType": "Encounter",
        "id": str(row["id"]),
        "status": row["status"] or "in-progress",
        "class": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": row["class_code"],
                        "display": row["class_display"] or row["class_code"],
                    }
                ]
            }
        ],
        "subject": {"reference": f"Patient/{row['patient_hn']}"},
        "actualPeriod": {
            "start": _dt(row["period_start"]),
        },
    }
    if row["period_end"]:
        resource["actualPeriod"]["end"] = _dt(row["period_end"])
    if row["reason"]:
        resource["reason"] = [{"value": [{"concept": {"text": row["reason"]}}]}]
    return resource


async def list_encounters(patient_hn: Optional[str] = None) -> list[dict]:
    pool = get_pool()
    if patient_hn:
        rows = await pool.fetch(
            "SELECT * FROM encounters WHERE patient_hn = $1 ORDER BY period_start DESC",
            patient_hn,
        )
    else:
        rows = await pool.fetch("SELECT * FROM encounters ORDER BY period_start DESC")
    return [_encounter_to_fhir(r) for r in rows]


async def get_encounter(enc_id: int) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM encounters WHERE id = $1", enc_id)
    return _encounter_to_fhir(row) if row else None


async def create_encounter(data: dict) -> dict:
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    if not patient_hn:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="subject.reference (Patient HN) is required.")

    exists = await pool.fetchval("SELECT hn FROM patients WHERE hn = $1", patient_hn)
    if not exists:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Patient {patient_hn!r} not found.")

    status_ = data.get("status", "in-progress")
    # R5: class is a list of CodeableConcept
    class_list = data.get("class") or [{}]
    class_item = class_list[0] if isinstance(class_list, list) else class_list
    class_coding = (class_item.get("coding") or [{}])[0]
    class_code = class_coding.get("code", "AMB")
    class_display = class_coding.get("display", "")

    # R5: actualPeriod replaces period
    period = data.get("actualPeriod") or data.get("period") or {}
    period_start_raw = period.get("start")
    period_end_raw = period.get("end")
    from datetime import datetime
    period_start = datetime.fromisoformat(period_start_raw).replace(tzinfo=None) if period_start_raw else datetime.now()
    period_end = datetime.fromisoformat(period_end_raw).replace(tzinfo=None) if period_end_raw else None

    # R5: reason[].value[].concept.text
    reason_list = data.get("reason") or []
    reason = None
    if reason_list:
        val = reason_list[0].get("value") or []
        reason = (val[0].get("concept") or {}).get("text") if val else None

    row = await pool.fetchrow(
        """
        INSERT INTO encounters (patient_hn, status, class_code, class_display, period_start, period_end, reason)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        patient_hn, status_, class_code, class_display, period_start, period_end, reason,
    )
    return _encounter_to_fhir(row)


async def update_encounter(enc_id: int, data: dict) -> Optional[dict]:
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    status_ = data.get("status", "in-progress")
    class_list = data.get("class") or [{}]
    class_item = class_list[0] if isinstance(class_list, list) else class_list
    class_coding = (class_item.get("coding") or [{}])[0]
    class_code = class_coding.get("code", "AMB")
    class_display = class_coding.get("display", "")

    period = data.get("actualPeriod") or data.get("period") or {}
    period_start_raw = period.get("start")
    period_end_raw = period.get("end")
    from datetime import datetime
    period_start = datetime.fromisoformat(period_start_raw).replace(tzinfo=None) if period_start_raw else datetime.now()
    period_end = datetime.fromisoformat(period_end_raw).replace(tzinfo=None) if period_end_raw else None

    reason_list = data.get("reason") or []
    reason = None
    if reason_list:
        val = reason_list[0].get("value") or []
        reason = (val[0].get("concept") or {}).get("text") if val else None

    row = await pool.fetchrow(
        """
        UPDATE encounters
        SET patient_hn=$2, status=$3, class_code=$4, class_display=$5,
            period_start=$6, period_end=$7, reason=$8
        WHERE id=$1
        RETURNING *
        """,
        enc_id, patient_hn, status_, class_code, class_display, period_start, period_end, reason,
    )
    return _encounter_to_fhir(row) if row else None


async def delete_encounter(enc_id: int) -> bool:
    pool = get_pool()
    result = await pool.execute("DELETE FROM encounters WHERE id = $1", enc_id)
    return result != "DELETE 0"


# ---------------------------------------------------------------------------
# Condition – helpers + CRUD
# ---------------------------------------------------------------------------

def _condition_to_fhir(row: Any) -> dict:
    resource: dict = {
        "resourceType": "Condition",
        "id": str(row["id"]),
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": row["clinical_status"],
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": row["icd10_code"],
                    "display": row["icd10_display"] or row["icd10_code"],
                }
            ]
        },
        "subject": {"reference": f"Patient/{row['patient_hn']}"},
    }
    if row["onset_date"]:
        resource["onsetDateTime"] = row["onset_date"].isoformat()
    if row["note"]:
        resource["note"] = [{"text": row["note"]}]
    return resource


async def list_conditions(patient_hn: Optional[str] = None) -> list[dict]:
    pool = get_pool()
    if patient_hn:
        rows = await pool.fetch(
            "SELECT * FROM conditions WHERE patient_hn = $1 ORDER BY created_at DESC",
            patient_hn,
        )
    else:
        rows = await pool.fetch("SELECT * FROM conditions ORDER BY created_at DESC")
    return [_condition_to_fhir(r) for r in rows]


async def get_condition(cond_id: int) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM conditions WHERE id = $1", cond_id)
    return _condition_to_fhir(row) if row else None


async def create_condition(data: dict) -> dict:
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    if not patient_hn:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="subject.reference (Patient HN) is required.")

    exists = await pool.fetchval("SELECT hn FROM patients WHERE hn = $1", patient_hn)
    if not exists:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Patient {patient_hn!r} not found.")

    clinical_status = (
        ((data.get("clinicalStatus") or {}).get("coding") or [{}])[0].get("code", "active")
    )
    coding = ((data.get("code") or {}).get("coding") or [{}])[0]
    icd10_code = coding.get("code", "")
    icd10_display = coding.get("display", "")

    onset_raw = data.get("onsetDateTime")
    from datetime import date
    onset_date = date.fromisoformat(onset_raw[:10]) if onset_raw else None

    notes = data.get("note") or []
    note = notes[0].get("text") if notes else None

    row = await pool.fetchrow(
        """
        INSERT INTO conditions (patient_hn, clinical_status, icd10_code, icd10_display, onset_date, note)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        patient_hn, clinical_status, icd10_code, icd10_display, onset_date, note,
    )
    return _condition_to_fhir(row)


async def update_condition(cond_id: int, data: dict) -> Optional[dict]:
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    clinical_status = (
        ((data.get("clinicalStatus") or {}).get("coding") or [{}])[0].get("code", "active")
    )
    coding = ((data.get("code") or {}).get("coding") or [{}])[0]
    icd10_code = coding.get("code", "")
    icd10_display = coding.get("display", "")

    onset_raw = data.get("onsetDateTime")
    from datetime import date
    onset_date = date.fromisoformat(onset_raw[:10]) if onset_raw else None

    notes = data.get("note") or []
    note = notes[0].get("text") if notes else None

    row = await pool.fetchrow(
        """
        UPDATE conditions
        SET patient_hn=$2, clinical_status=$3, icd10_code=$4, icd10_display=$5,
            onset_date=$6, note=$7
        WHERE id=$1
        RETURNING *
        """,
        cond_id, patient_hn, clinical_status, icd10_code, icd10_display, onset_date, note,
    )
    return _condition_to_fhir(row) if row else None


async def delete_condition(cond_id: int) -> bool:
    pool = get_pool()
    result = await pool.execute("DELETE FROM conditions WHERE id = $1", cond_id)
    return result != "DELETE 0"


# ---------------------------------------------------------------------------
# MedicationRequest – helpers + CRUD
# ---------------------------------------------------------------------------

def _medication_request_to_fhir(row: Any) -> dict:
    return {
        "resourceType": "MedicationRequest",
        "id": str(row["id"]),
        "status": row["status"] or "active",
        "intent": row["intent"] or "order",
        "medication": {
            "concept": {
                "coding": [
                    {
                        "system": "http://www.whocc.no/atc",
                        "code": row["atc_code"],
                        "display": row["medication_display"] or row["atc_code"],
                    }
                ]
            }
        },
        "subject": {"reference": f"Patient/{row['patient_hn']}"},
        "dosageInstruction": [{"text": row["dosage_text"] or ""}] if row["dosage_text"] else [],
        "authoredOn": row["authored_on"].isoformat(),
    }


async def list_medication_requests(patient_hn: Optional[str] = None) -> list[dict]:
    pool = get_pool()
    if patient_hn:
        rows = await pool.fetch(
            "SELECT * FROM medication_requests WHERE patient_hn = $1 ORDER BY authored_on DESC",
            patient_hn,
        )
    else:
        rows = await pool.fetch("SELECT * FROM medication_requests ORDER BY authored_on DESC")
    return [_medication_request_to_fhir(r) for r in rows]


async def get_medication_request(mr_id: int) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM medication_requests WHERE id = $1", mr_id)
    return _medication_request_to_fhir(row) if row else None


async def create_medication_request(data: dict) -> dict:
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    if not patient_hn:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="subject.reference (Patient HN) is required.")

    exists = await pool.fetchval("SELECT hn FROM patients WHERE hn = $1", patient_hn)
    if not exists:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Patient {patient_hn!r} not found.")

    status_ = data.get("status", "active")
    intent = data.get("intent", "order")

    med_concept = (data.get("medication") or {}).get("concept") or {}
    coding = (med_concept.get("coding") or [{}])[0]
    atc_code = coding.get("code", "")
    medication_display = coding.get("display", "")

    dosage_list = data.get("dosageInstruction") or []
    dosage_text = dosage_list[0].get("text") if dosage_list else None

    authored_raw = data.get("authoredOn")
    from datetime import datetime
    authored_on = datetime.fromisoformat(authored_raw).replace(tzinfo=None) if authored_raw else datetime.now()

    row = await pool.fetchrow(
        """
        INSERT INTO medication_requests (patient_hn, status, intent, atc_code, medication_display, dosage_text, authored_on)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        patient_hn, status_, intent, atc_code, medication_display, dosage_text, authored_on,
    )
    return _medication_request_to_fhir(row)


async def update_medication_request(mr_id: int, data: dict) -> Optional[dict]:
    pool = get_pool()
    subject = (data.get("subject") or {}).get("reference", "")
    patient_hn = subject.split("/")[-1] if "/" in subject else subject

    status_ = data.get("status", "active")
    intent = data.get("intent", "order")

    med_concept = (data.get("medication") or {}).get("concept") or {}
    coding = (med_concept.get("coding") or [{}])[0]
    atc_code = coding.get("code", "")
    medication_display = coding.get("display", "")

    dosage_list = data.get("dosageInstruction") or []
    dosage_text = dosage_list[0].get("text") if dosage_list else None

    authored_raw = data.get("authoredOn")
    from datetime import datetime
    authored_on = datetime.fromisoformat(authored_raw).replace(tzinfo=None) if authored_raw else datetime.now()

    row = await pool.fetchrow(
        """
        UPDATE medication_requests
        SET patient_hn=$2, status=$3, intent=$4, atc_code=$5,
            medication_display=$6, dosage_text=$7, authored_on=$8
        WHERE id=$1
        RETURNING *
        """,
        mr_id, patient_hn, status_, intent, atc_code, medication_display, dosage_text, authored_on,
    )
    return _medication_request_to_fhir(row) if row else None


async def delete_medication_request(mr_id: int) -> bool:
    pool = get_pool()
    result = await pool.execute("DELETE FROM medication_requests WHERE id = $1", mr_id)
    return result != "DELETE 0"
