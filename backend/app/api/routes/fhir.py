"""
FHIR CRUD routes for: Patient, ServiceRequest, Specimen, Observation, DiagnosticReport.

Uses fhir.resources 8.x (FHIR R5) for payload validation.
All routes are protected by JWT authentication.
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError

# fhir.resources 8.x targets FHIR R5 at the top-level package.
from fhir.resources.patient import Patient
from fhir.resources.servicerequest import ServiceRequest
from fhir.resources.specimen import Specimen
from fhir.resources.observation import Observation
from fhir.resources.diagnosticreport import DiagnosticReport

from app.api.deps import verify_token
from app.db import repository

router = APIRouter(prefix="/fhir", tags=["fhir"])

# --- Registry -----------------------------------------------------------------

FHIR_MODELS: dict[str, Any] = {
    "Patient": Patient,
    "ServiceRequest": ServiceRequest,
    "Specimen": Specimen,
    "Observation": Observation,
    "DiagnosticReport": DiagnosticReport,
}


def _resolve_model(resource_type: str) -> Any:
    model = FHIR_MODELS.get(resource_type)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown FHIR resource type: '{resource_type}'. "
            f"Supported: {sorted(FHIR_MODELS)}",
        )
    return model


# --- Helpers ------------------------------------------------------------------


def _validate_fhir(resource_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate payload with the fhir.resources model and return a clean dict."""
    model_cls = _resolve_model(resource_type)
    # Ensure the resourceType field is present so fhir.resources can validate it.
    payload.setdefault("resourceType", resource_type)
    try:
        instance = model_cls.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"fhir_validation_errors": json.loads(exc.json())},
        )
    # model_dump_json + json.loads ensures all FHIR types are JSON-serialisable.
    return json.loads(instance.model_dump_json(exclude_none=True))


def _extract_patient_id(resource_type: str, data: dict[str, Any]) -> Optional[str]:
    """Extract the patient FHIR id from the resource data."""
    if resource_type == "Patient":
        return data.get("id")
    # All other supported resources carry subject.reference = "Patient/<id>"
    subject = data.get("subject") or data.get("patient")
    if isinstance(subject, dict):
        ref: str = subject.get("reference", "")
        return ref.split("/")[-1] if "/" in ref else (ref or None)
    return None


# --- CRUD endpoints -----------------------------------------------------------


@router.post("/{resource_type}", status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource_type: str,
    payload: dict[str, Any] = Body(...),
    _user: str = Depends(verify_token),
) -> dict[str, Any]:
    _resolve_model(resource_type)  # early 404 if unknown type
    clean_data = _validate_fhir(resource_type, payload)
    patient_id = _extract_patient_id(resource_type, clean_data)
    record = await repository.create_resource(resource_type, patient_id, clean_data)
    return record["data"]


@router.get("/{resource_type}")
async def list_resources(
    resource_type: str,
    _user: str = Depends(verify_token),
) -> list[dict[str, Any]]:
    _resolve_model(resource_type)
    records = await repository.list_resources(resource_type)
    return [r["data"] for r in records]


@router.get("/{resource_type}/{resource_id}")
async def get_resource(
    resource_type: str,
    resource_id: str,
    _user: str = Depends(verify_token),
) -> dict[str, Any]:
    _resolve_model(resource_type)
    record = await repository.get_resource(resource_type, resource_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type}/{resource_id} not found.",
        )
    return record["data"]


@router.put("/{resource_type}/{resource_id}")
async def update_resource(
    resource_type: str,
    resource_id: str,
    payload: dict[str, Any] = Body(...),
    _user: str = Depends(verify_token),
) -> dict[str, Any]:
    _resolve_model(resource_type)
    clean_data = _validate_fhir(resource_type, payload)
    patient_id = _extract_patient_id(resource_type, clean_data)
    record = await repository.update_resource(
        resource_type, resource_id, patient_id, clean_data
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type}/{resource_id} not found.",
        )
    return record["data"]


@router.delete("/{resource_type}/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_type: str,
    resource_id: str,
    _user: str = Depends(verify_token),
) -> None:
    _resolve_model(resource_type)
    deleted = await repository.delete_resource(resource_type, resource_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type}/{resource_id} not found.",
        )
