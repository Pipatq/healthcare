"""
HIS B FHIR Facade routes.

Supported resources: Patient, Observation, ServiceRequest
All endpoints require X-API-Key authentication (called by the FHIR Gateway).
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import ValidationError

from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.servicerequest import ServiceRequest

from app.api.deps import verify_api_key
from app.db import repository

router = APIRouter(tags=["fhir"])

# ---------------------------------------------------------------------------
# Internal validation helpers
# ---------------------------------------------------------------------------

_FHIR_MODELS: dict[str, Any] = {
    "Patient": Patient,
    "Observation": Observation,
    "ServiceRequest": ServiceRequest,
}


def _validate_fhir(resource_type: str, payload: dict) -> dict:
    model_cls = _FHIR_MODELS.get(resource_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail=f"Unsupported resource: {resource_type}")
    payload.setdefault("resourceType", resource_type)
    try:
        instance = model_cls.model_validate(payload)
    except ValidationError as exc:
        logger.warning("FHIR validation failed for {}: {}", resource_type, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"fhir_validation_errors": json.loads(exc.json())},
        )
    return json.loads(instance.model_dump_json(exclude_none=True))


# ---------------------------------------------------------------------------
# Patient endpoints
# ---------------------------------------------------------------------------


@router.get("/Patient", summary="List all patients (FHIR Patient[])",
    description="ดึงรายชื่อผู้ป่วยทั้งหมด\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def list_patients(
    _: str = Depends(verify_api_key),
) -> list[dict]:
    patients = await repository.list_patients()
    logger.info("Listed {} patients", len(patients))
    return patients


@router.get("/Patient/{patient_id}", summary="Get patient by HN",
    description="ดึงข้อมูลผู้ป่วยด้วย HN\n\n**ตัวอย่าง patient_id:** `HN-0001`, `HN-0002`, `HN-0003`, `HN-0004`, `HN-0005`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def get_patient(
    patient_id: str,
    _: str = Depends(verify_api_key),
) -> dict:
    patient = await repository.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id!r} not found.")
    return patient


@router.post("/Patient", status_code=status.HTTP_201_CREATED, summary="Create / upsert a patient",
    description="สร้างหรืออัปเดตข้อมูลผู้ป่วย (FHIR Patient resource)\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง body:**\n```json\n{\n  \"resourceType\": \"Patient\",\n  \"id\": \"HN-0099\",\n  \"identifier\": [{\"system\": \"urn:his-b:hn\", \"value\": \"HN-0099\"}],\n  \"name\": [{\"family\": \"ทดสอบ\", \"given\": [\"ผู้ป่วย\"]}],\n  \"gender\": \"male\",\n  \"birthDate\": \"1990-01-01\"\n}\n```")
async def create_patient(
    payload: dict[str, Any] = Body(...),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Patient", payload)
    result = await repository.create_patient(clean)
    logger.info("Upserted patient HN={}", result.get("id"))
    return result


# ---------------------------------------------------------------------------
# Observation endpoints
# ---------------------------------------------------------------------------


@router.get("/Observation", summary="List observations (optionally filter by patient HN)",
    description="ดึงผลแลบทั้งหมด หรือกรองด้วย patient HN\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง patient:** `HN-0001`, `HN-0002`, `HN-0003`")
async def list_observations(
    patient: Optional[str] = Query(None, description="Filter by patient HN — ตัวอย่าง: HN-0001, HN-0002, HN-0003"),
    _: str = Depends(verify_api_key),
) -> list[dict]:
    # Accept both ?patient=HN-0001 and ?patient=Patient/HN-0001
    hn = patient.split("/")[-1] if patient and "/" in patient else patient
    observations = await repository.list_observations(hn)
    logger.info("Listed {} observations (patient={})", len(observations), hn)
    return observations


@router.get("/Observation/{obs_id}", summary="Get observation by ID",
    description="ดึงผลแลบด้วย ID (ตัวเลข)\n\n**ตัวอย่าง obs_id:** `1`, `2`, `3`, `4`, `5`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def get_observation(
    obs_id: int,
    _: str = Depends(verify_api_key),
) -> dict:
    obs = await repository.get_observation(obs_id)
    if not obs:
        raise HTTPException(status_code=404, detail=f"Observation {obs_id} not found.")
    return obs


# ---------------------------------------------------------------------------
# ServiceRequest endpoints
# ---------------------------------------------------------------------------


@router.get("/ServiceRequest", summary="List service requests (optionally filter by patient HN)",
    description="ดึงคำสั่งแพทย์ทั้งหมด หรือกรองด้วย patient HN\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง patient:** `HN-0001`, `HN-0002`, `HN-0003`")
async def list_service_requests(
    patient: Optional[str] = Query(None, description="Filter by patient HN — ตัวอย่าง: HN-0001, HN-0002, HN-0003"),
    _: str = Depends(verify_api_key),
) -> list[dict]:
    hn = patient.split("/")[-1] if patient and "/" in patient else patient
    requests = await repository.list_service_requests(hn)
    logger.info("Listed {} service requests (patient={})", len(requests), hn)
    return requests


@router.get("/ServiceRequest/{sr_id}", summary="Get service request by ID",
    description="ดึงคำสั่งแพทย์ด้วย ID (ตัวเลข)\n\n**ตัวอย่าง sr_id:** `1`, `2`, `3`, `4`, `5`, `6`, `7`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def get_service_request(
    sr_id: int,
    _: str = Depends(verify_api_key),
) -> dict:
    sr = await repository.get_service_request(sr_id)
    if not sr:
        raise HTTPException(status_code=404, detail=f"ServiceRequest {sr_id} not found.")
    return sr
