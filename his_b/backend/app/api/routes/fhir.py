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
from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.medicationrequest import MedicationRequest

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
    "Encounter": Encounter,
    "Condition": Condition,
    "MedicationRequest": MedicationRequest,
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


# ---------------------------------------------------------------------------
# Patient – PUT / DELETE
# ---------------------------------------------------------------------------


@router.put("/Patient/{patient_id}", summary="Update patient by HN",
    description="อัปเดตข้อมูลผู้ป่วย\n\n**ตัวอย่าง patient_id:** `HN-0001`\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง body:**\n```json\n{\n  \"resourceType\": \"Patient\",\n  \"id\": \"HN-0001\",\n  \"name\": [{\"family\": \"ใจดี\", \"given\": [\"สมชาย\"]}],\n  \"gender\": \"male\",\n  \"birthDate\": \"1980-05-15\",\n  \"telecom\": [{\"system\": \"phone\", \"value\": \"0899999999\"}]\n}\n```")
async def update_patient(
    patient_id: str,
    payload: dict[str, Any] = Body(...),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Patient", payload)
    result = await repository.update_patient(patient_id, clean)
    if not result:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id!r} not found.")
    logger.info("Updated patient HN={}", patient_id)
    return result


@router.delete("/Patient/{patient_id}", status_code=204, summary="Delete patient by HN",
    description="ลบผู้ป่วยด้วย HN\n\n**ตัวอย่าง patient_id:** `HN-0099`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def delete_patient(
    patient_id: str,
    _: str = Depends(verify_api_key),
) -> None:
    deleted = await repository.delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id!r} not found.")
    logger.info("Deleted patient HN={}", patient_id)


# ---------------------------------------------------------------------------
# Observation – POST / PUT / DELETE
# ---------------------------------------------------------------------------


@router.post("/Observation", status_code=201, summary="Create a new observation",
    description="บันทึกผลแลบใหม่\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง body:**\n```json\n{\n  \"resourceType\": \"Observation\",\n  \"status\": \"final\",\n  \"code\": {\"coding\": [{\"system\": \"http://loinc.org\", \"code\": \"718-7\", \"display\": \"Hemoglobin\"}]},\n  \"subject\": {\"reference\": \"Patient/HN-0001\"},\n  \"issued\": \"2026-04-23T10:00:00+07:00\",\n  \"valueQuantity\": {\"value\": 13.5, \"unit\": \"g/dL\", \"system\": \"http://unitsofmeasure.org\", \"code\": \"g/dL\"}\n}\n```")
async def create_observation(
    payload: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "hemoglobin": {
                "summary": "ผลแลบ Hemoglobin ของ HN-0001",
                "value": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "718-7", "display": "Hemoglobin"}]},
                    "subject": {"reference": "Patient/HN-0001"},
                    "issued": "2026-04-23T10:00:00+07:00",
                    "valueQuantity": {"value": 13.5, "unit": "g/dL", "system": "http://unitsofmeasure.org", "code": "g/dL"},
                },
            },
            "blood_pressure": {
                "summary": "ผลแลบ Blood Pressure ของ HN-0005",
                "value": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "55284-4", "display": "Blood pressure panel"}]},
                    "subject": {"reference": "Patient/HN-0005"},
                    "issued": "2026-04-23T10:00:00+07:00",
                    "valueQuantity": {"value": 120, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
                },
            },
        },
    ),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Observation", payload)
    result = await repository.create_observation(clean)
    logger.info("Created observation id={}", result.get("id"))
    return result


@router.put("/Observation/{obs_id}", summary="Update observation by ID",
    description="อัปเดตผลแลบด้วย ID\n\n**ตัวอย่าง obs_id:** `1`, `2`, `3`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def update_observation(
    obs_id: int,
    payload: dict[str, Any] = Body(...),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Observation", payload)
    result = await repository.update_observation(obs_id, clean)
    if not result:
        raise HTTPException(status_code=404, detail=f"Observation {obs_id} not found.")
    logger.info("Updated observation id={}", obs_id)
    return result


@router.delete("/Observation/{obs_id}", status_code=204, summary="Delete observation by ID",
    description="ลบผลแลบด้วย ID\n\n**ตัวอย่าง obs_id:** `1`, `2`, `3`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def delete_observation(
    obs_id: int,
    _: str = Depends(verify_api_key),
) -> None:
    deleted = await repository.delete_observation(obs_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Observation {obs_id} not found.")
    logger.info("Deleted observation id={}", obs_id)


# ---------------------------------------------------------------------------
# ServiceRequest – POST / PUT / DELETE
# ---------------------------------------------------------------------------


@router.post("/ServiceRequest", status_code=201, summary="Create a new service request",
    description="สร้างคำสั่งแพทย์ใหม่\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง body:**\n```json\n{\n  \"resourceType\": \"ServiceRequest\",\n  \"status\": \"active\",\n  \"intent\": \"order\",\n  \"priority\": \"routine\",\n  \"code\": {\"coding\": [{\"system\": \"urn:his-b:order-codes\", \"code\": \"CBC-001\", \"display\": \"Complete Blood Count\"}]},\n  \"subject\": {\"reference\": \"Patient/HN-0001\"}\n}\n```")
async def create_service_request(
    payload: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "cbc": {
                "summary": "สั่ง CBC ให้ HN-0001",
                "value": {
                    "resourceType": "ServiceRequest",
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "code": {"coding": [{"system": "urn:his-b:order-codes", "code": "CBC-001", "display": "Complete Blood Count"}]},
                    "subject": {"reference": "Patient/HN-0001"},
                },
            },
            "lipid_urgent": {
                "summary": "สั่ง Lipid Panel ด่วน ให้ HN-0004",
                "value": {
                    "resourceType": "ServiceRequest",
                    "status": "active",
                    "intent": "order",
                    "priority": "urgent",
                    "code": {"coding": [{"system": "urn:his-b:order-codes", "code": "LIPID-001", "display": "Lipid Panel"}]},
                    "subject": {"reference": "Patient/HN-0004"},
                },
            },
        },
    ),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("ServiceRequest", payload)
    result = await repository.create_service_request(clean)
    logger.info("Created ServiceRequest id={}", result.get("id"))
    return result


@router.put("/ServiceRequest/{sr_id}", summary="Update service request by ID",
    description="อัปเดตคำสั่งแพทย์ด้วย ID\n\n**ตัวอย่าง sr_id:** `1`, `2`, `3`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def update_service_request(
    sr_id: int,
    payload: dict[str, Any] = Body(...),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("ServiceRequest", payload)
    result = await repository.update_service_request(sr_id, clean)
    if not result:
        raise HTTPException(status_code=404, detail=f"ServiceRequest {sr_id} not found.")
    logger.info("Updated ServiceRequest id={}", sr_id)
    return result


@router.delete("/ServiceRequest/{sr_id}", status_code=204, summary="Delete service request by ID",
    description="ลบคำสั่งแพทย์ด้วย ID\n\n**ตัวอย่าง sr_id:** `1`, `2`, `3`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def delete_service_request(
    sr_id: int,
    _: str = Depends(verify_api_key),
) -> None:
    deleted = await repository.delete_service_request(sr_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"ServiceRequest {sr_id} not found.")
    logger.info("Deleted ServiceRequest id={}", sr_id)


# ---------------------------------------------------------------------------
# Encounter endpoints
# ---------------------------------------------------------------------------


@router.get("/Encounter", summary="List encounters (optionally filter by patient HN)",
    description="ดึงข้อมูลการเข้ารับบริการทั้งหมด\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง patient:** `HN-0001`, `HN-0003`")
async def list_encounters(
    patient: Optional[str] = Query(None, description="Filter by patient HN — ตัวอย่าง: HN-0001, HN-0003"),
    _: str = Depends(verify_api_key),
) -> list[dict]:
    hn = patient.split("/")[-1] if patient and "/" in patient else patient
    encounters = await repository.list_encounters(hn)
    logger.info("Listed {} encounters (patient={})", len(encounters), hn)
    return encounters


@router.get("/Encounter/{enc_id}", summary="Get encounter by ID",
    description="ดึงข้อมูลการเข้ารับบริการด้วย ID\n\n**ตัวอย่าง enc_id:** `1`, `2`, `3`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def get_encounter(
    enc_id: int,
    _: str = Depends(verify_api_key),
) -> dict:
    enc = await repository.get_encounter(enc_id)
    if not enc:
        raise HTTPException(status_code=404, detail=f"Encounter {enc_id} not found.")
    return enc


@router.post("/Encounter", status_code=201, summary="Create a new encounter",
    description="บันทึกการเข้ารับบริการใหม่\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def create_encounter(
    payload: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "outpatient": {
                "summary": "OPD visit ของ HN-0001",
                "value": {
                    "resourceType": "Encounter",
                    "status": "in-progress",
                    "class": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "outpatient encounter"}]}],
                    "subject": {"reference": "Patient/HN-0001"},
                    "actualPeriod": {"start": "2026-04-24T09:00:00"},
                    "reason": [{"value": [{"concept": {"text": "Follow-up diabetes"}}]}],
                },
            },
            "inpatient": {
                "summary": "IPD admit ของ HN-0003",
                "value": {
                    "resourceType": "Encounter",
                    "status": "in-progress",
                    "class": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "inpatient encounter"}]}],
                    "subject": {"reference": "Patient/HN-0003"},
                    "actualPeriod": {"start": "2026-04-22T07:00:00"},
                    "reason": [{"value": [{"concept": {"text": "Acute renal failure"}}]}],
                },
            },
        },
    ),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Encounter", payload)
    result = await repository.create_encounter(clean)
    logger.info("Created Encounter id={}", result.get("id"))
    return result


@router.put("/Encounter/{enc_id}", summary="Update encounter by ID",
    description="อัปเดตข้อมูลการเข้ารับบริการ\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def update_encounter(
    enc_id: int,
    payload: dict[str, Any] = Body(...),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Encounter", payload)
    result = await repository.update_encounter(enc_id, clean)
    if not result:
        raise HTTPException(status_code=404, detail=f"Encounter {enc_id} not found.")
    logger.info("Updated Encounter id={}", enc_id)
    return result


@router.delete("/Encounter/{enc_id}", status_code=204, summary="Delete encounter by ID",
    description="ลบข้อมูลการเข้ารับบริการ\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def delete_encounter(
    enc_id: int,
    _: str = Depends(verify_api_key),
) -> None:
    deleted = await repository.delete_encounter(enc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Encounter {enc_id} not found.")
    logger.info("Deleted Encounter id={}", enc_id)


# ---------------------------------------------------------------------------
# Condition endpoints
# ---------------------------------------------------------------------------


@router.get("/Condition", summary="List conditions (optionally filter by patient HN)",
    description="ดึงการวินิจฉัยโรค (ICD-10) ทั้งหมด\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง patient:** `HN-0001`, `HN-0002`")
async def list_conditions(
    patient: Optional[str] = Query(None, description="Filter by patient HN — ตัวอย่าง: HN-0001, HN-0002"),
    _: str = Depends(verify_api_key),
) -> list[dict]:
    hn = patient.split("/")[-1] if patient and "/" in patient else patient
    conditions = await repository.list_conditions(hn)
    logger.info("Listed {} conditions (patient={})", len(conditions), hn)
    return conditions


@router.get("/Condition/{cond_id}", summary="Get condition by ID",
    description="ดึงการวินิจฉัยโรคด้วย ID\n\n**ตัวอย่าง cond_id:** `1`, `2`, `3`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def get_condition(
    cond_id: int,
    _: str = Depends(verify_api_key),
) -> dict:
    cond = await repository.get_condition(cond_id)
    if not cond:
        raise HTTPException(status_code=404, detail=f"Condition {cond_id} not found.")
    return cond


@router.post("/Condition", status_code=201, summary="Create a new condition",
    description="บันทึกการวินิจฉัยโรคใหม่ (FHIR Condition)\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def create_condition(
    payload: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "diabetes": {
                "summary": "วินิจฉัย DM Type 2 ให้ HN-0001",
                "value": {
                    "resourceType": "Condition",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "E11", "display": "Type 2 diabetes mellitus"}]},
                    "subject": {"reference": "Patient/HN-0001"},
                    "onsetDateTime": "2024-01-01",
                },
            },
            "hypertension": {
                "summary": "วินิจฉัย Hypertension ให้ HN-0002",
                "value": {
                    "resourceType": "Condition",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I10", "display": "Essential (primary) hypertension"}]},
                    "subject": {"reference": "Patient/HN-0002"},
                    "onsetDateTime": "2022-06-15",
                },
            },
        },
    ),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Condition", payload)
    result = await repository.create_condition(clean)
    logger.info("Created Condition id={}", result.get("id"))
    return result


@router.put("/Condition/{cond_id}", summary="Update condition by ID",
    description="อัปเดตการวินิจฉัยโรค\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def update_condition(
    cond_id: int,
    payload: dict[str, Any] = Body(...),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("Condition", payload)
    result = await repository.update_condition(cond_id, clean)
    if not result:
        raise HTTPException(status_code=404, detail=f"Condition {cond_id} not found.")
    logger.info("Updated Condition id={}", cond_id)
    return result


@router.delete("/Condition/{cond_id}", status_code=204, summary="Delete condition by ID",
    description="ลบการวินิจฉัยโรค\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def delete_condition(
    cond_id: int,
    _: str = Depends(verify_api_key),
) -> None:
    deleted = await repository.delete_condition(cond_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Condition {cond_id} not found.")
    logger.info("Deleted Condition id={}", cond_id)


# ---------------------------------------------------------------------------
# MedicationRequest endpoints
# ---------------------------------------------------------------------------


@router.get("/MedicationRequest", summary="List medication requests (optionally filter by patient HN)",
    description="ดึงรายการยาที่สั่งทั้งหมด\n\n**API Key (X-API-Key):** `his-b-secret-key`\n\n**ตัวอย่าง patient:** `HN-0001`, `HN-0005`")
async def list_medication_requests(
    patient: Optional[str] = Query(None, description="Filter by patient HN — ตัวอย่าง: HN-0001, HN-0005"),
    _: str = Depends(verify_api_key),
) -> list[dict]:
    hn = patient.split("/")[-1] if patient and "/" in patient else patient
    med_requests = await repository.list_medication_requests(hn)
    logger.info("Listed {} medication requests (patient={})", len(med_requests), hn)
    return med_requests


@router.get("/MedicationRequest/{mr_id}", summary="Get medication request by ID",
    description="ดึงรายการยาด้วย ID\n\n**ตัวอย่าง mr_id:** `1`, `2`, `3`\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def get_medication_request(
    mr_id: int,
    _: str = Depends(verify_api_key),
) -> dict:
    mr = await repository.get_medication_request(mr_id)
    if not mr:
        raise HTTPException(status_code=404, detail=f"MedicationRequest {mr_id} not found.")
    return mr


@router.post("/MedicationRequest", status_code=201, summary="Create a new medication request",
    description="สั่งยาใหม่ (FHIR MedicationRequest)\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def create_medication_request(
    payload: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "metformin": {
                "summary": "สั่ง Metformin ให้ HN-0001",
                "value": {
                    "resourceType": "MedicationRequest",
                    "status": "active",
                    "intent": "order",
                    "medication": {"concept": {"coding": [{"system": "http://www.whocc.no/atc", "code": "A10BA02", "display": "Metformin"}]}},
                    "subject": {"reference": "Patient/HN-0001"},
                    "dosageInstruction": [{"text": "500mg twice daily with meals"}],
                    "authoredOn": "2026-04-24T08:00:00",
                },
            },
            "aspirin": {
                "summary": "สั่ง Aspirin ให้ HN-0005",
                "value": {
                    "resourceType": "MedicationRequest",
                    "status": "active",
                    "intent": "order",
                    "medication": {"concept": {"coding": [{"system": "http://www.whocc.no/atc", "code": "B01AC06", "display": "Aspirin"}]}},
                    "subject": {"reference": "Patient/HN-0005"},
                    "dosageInstruction": [{"text": "100mg once daily"}],
                    "authoredOn": "2026-04-24T08:00:00",
                },
            },
        },
    ),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("MedicationRequest", payload)
    result = await repository.create_medication_request(clean)
    logger.info("Created MedicationRequest id={}", result.get("id"))
    return result


@router.put("/MedicationRequest/{mr_id}", summary="Update medication request by ID",
    description="อัปเดตรายการยา\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def update_medication_request(
    mr_id: int,
    payload: dict[str, Any] = Body(...),
    _: str = Depends(verify_api_key),
) -> dict:
    clean = _validate_fhir("MedicationRequest", payload)
    result = await repository.update_medication_request(mr_id, clean)
    if not result:
        raise HTTPException(status_code=404, detail=f"MedicationRequest {mr_id} not found.")
    logger.info("Updated MedicationRequest id={}", mr_id)
    return result


@router.delete("/MedicationRequest/{mr_id}", status_code=204, summary="Delete medication request by ID",
    description="ลบรายการยา\n\n**API Key (X-API-Key):** `his-b-secret-key`")
async def delete_medication_request(
    mr_id: int,
    _: str = Depends(verify_api_key),
) -> None:
    deleted = await repository.delete_medication_request(mr_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"MedicationRequest {mr_id} not found.")
    logger.info("Deleted MedicationRequest id={}", mr_id)

