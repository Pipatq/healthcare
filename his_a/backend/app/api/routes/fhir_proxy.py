"""
HIS A – FHIR Proxy routes.

Doctor-facing endpoints: JWT-protected. Each request is forwarded to the
FHIR Gateway which routes it to HIS B, adding the inter-service API key.

Each HTTP method has its own decorated function so Swagger UI renders them
as separate, independently collapsible operations (fixes the "all-open" bug).
"""

import time
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.deps import verify_token
from app.core.config import settings

router = APIRouter(tags=["fhir-proxy"])

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized.")
    return _http_client


async def startup_client() -> None:
    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=settings.GATEWAY_BASE_URL,
        timeout=settings.PROXY_TIMEOUT,
        headers={"X-API-Key": settings.GATEWAY_API_KEY},
    )


async def shutdown_client() -> None:
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


# ─── Internal proxy helper ────────────────────────────────────────────────────

async def _proxy(
    method: str,
    path: str,
    doctor: str,
    params: dict,
    body: bytes | None = None,
) -> JSONResponse:
    target_url = f"/fhir/{path}"
    t0 = time.monotonic()
    try:
        client = get_http_client()
        response = await client.request(
            method=method,
            url=target_url,
            params=params,
            content=body or None,
            headers={"Content-Type": "application/json"},
        )
    except httpx.TimeoutException:
        logger.error("Timeout reaching Gateway for {} {}", method, target_url)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Gateway did not respond in time.",
        )
    except httpx.RequestError as exc:
        logger.error("Network error reaching Gateway: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cannot reach FHIR Gateway.",
        )

    latency_ms = round((time.monotonic() - t0) * 1000)
    logger.info(
        "HIS-A doctor={} → PROXY {} /fhir/{} → Gateway | status={} {}ms",
        doctor, method, path, response.status_code, latency_ms,
    )

    try:
        payload: Any = response.json()
    except Exception:
        payload = {"raw": response.text}

    return JSONResponse(content=payload, status_code=response.status_code)


# ─── GET ──────────────────────────────────────────────────────────────────────

@router.get(
    "/fhir/{path:path}",
    summary="GET — ดึงข้อมูล FHIR resource",
    operation_id="fhir_proxy_get",
    description="""
ดึงข้อมูล FHIR resource ผ่าน Gateway → HIS B  
ต้องใส่ **JWT Bearer token** (จาก `POST /api/v1/auth/login`)

### ตัวอย่าง path

| path | ความหมาย |
|------|-----------|
| `Patient` | ดูผู้ป่วยทั้งหมด |
| `Patient/HN-0001` | ดูผู้ป่วยรายเดียว |
| `Observation` | ดูผลแลบทั้งหมด |
| `Observation?patient=HN-0001` | ผลแลบของ HN-0001 |
| `ServiceRequest` | ดูคำสั่งแพทย์ทั้งหมด |
| `ServiceRequest?patient=HN-0001` | คำสั่งของ HN-0001 |
| `Encounter` | ดูข้อมูลการเข้ารับบริการทั้งหมด |
| `Encounter?patient=HN-0001` | การเข้ารับบริการของ HN-0001 |
| `Condition` | ดูการวินิจฉัยโรคทั้งหมด |
| `Condition?patient=HN-0001` | โรคที่วินิจฉัยของ HN-0001 |
| `MedicationRequest` | ดูรายการยาทั้งหมด |
| `MedicationRequest?patient=HN-0001` | ยาของ HN-0001 |
""",
)
async def fhir_get(
    request: Request,
    path: str,
    doctor: str = Depends(verify_token),
) -> JSONResponse:
    return await _proxy("GET", path, doctor, dict(request.query_params))


# ─── POST ─────────────────────────────────────────────────────────────────────

@router.post(
    "/fhir/{path:path}",
    summary="POST — สร้าง FHIR resource ใหม่",
    operation_id="fhir_proxy_post",
    status_code=201,
    description="""
สร้าง FHIR resource ใหม่ผ่าน Gateway → HIS B

### ตัวอย่าง path

| path | ความหมาย |
|------|-----------|
| `Patient` | สร้างผู้ป่วยใหม่ |
| `Observation` | บันทึกผลแลบใหม่ |
| `ServiceRequest` | สร้างคำสั่งแพทย์ใหม่ |

### Request Body — POST /fhir/Patient
```json
{
  "resourceType": "Patient",
  "id": "HN-0099",
  "identifier": [{"system": "urn:his-b:hn", "value": "HN-0099"}],
  "name": [{"family": "ทดสอบ", "given": ["ผู้ป่วย"]}],
  "gender": "male",
  "birthDate": "1990-01-01"
}
```

### Request Body — POST /fhir/Observation
```json
{
  "resourceType": "Observation",
  "status": "final",
  "code": {"coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine"}]},
  "subject": {"reference": "Patient/HN-0001"},
  "valueQuantity": {"value": 0.9, "unit": "mg/dL"}
}
```

### Request Body — POST /fhir/ServiceRequest
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "code": {"coding": [{"system": "urn:his-b:order-codes", "code": "CHEM-001", "display": "Comprehensive Metabolic Panel"}]},
  "subject": {"reference": "Patient/HN-0001"}
}
```

### Request Body — POST /fhir/Encounter
```json
{
  "resourceType": "Encounter",
  "status": "in-progress",
  "class": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "inpatient encounter"}]},
  "subject": {"reference": "Patient/HN-0001"},
  "period": {"start": "2026-04-24T08:00:00"}
}
```

### Request Body — POST /fhir/Condition
```json
{
  "resourceType": "Condition",
  "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
  "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "E11", "display": "Type 2 diabetes mellitus"}]},
  "subject": {"reference": "Patient/HN-0001"}
}
```

### Request Body — POST /fhir/MedicationRequest
```json
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medication": {"concept": {"coding": [{"system": "http://www.whocc.no/atc", "code": "A10BA02", "display": "Metformin"}]}},
  "subject": {"reference": "Patient/HN-0001"},
  "dosageInstruction": [{"text": "500 mg twice daily"}]
}
```
""",
)
async def fhir_post(
    request: Request,
    path: str,
    body: dict = Body(
        ...,
        openapi_examples={
            "Patient": {
                "summary": "POST /fhir/Patient",
                "value": {
                    "resourceType": "Patient",
                    "id": "HN-0099",
                    "identifier": [{"system": "urn:his-b:hn", "value": "HN-0099"}],
                    "name": [{"family": "ทดสอบ", "given": ["ผู้ป่วย"]}],
                    "gender": "male",
                    "birthDate": "1990-01-01",
                },
            },
            "Encounter": {
                "summary": "POST /fhir/Encounter",
                "value": {
                    "resourceType": "Encounter",
                    "status": "in-progress",
                    "class": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "inpatient encounter"}]}],
                    "subject": {"reference": "Patient/HN-0001"},
                    "actualPeriod": {"start": "2026-04-24T08:00:00"},
                },
            },
            "Condition": {
                "summary": "POST /fhir/Condition",
                "value": {
                    "resourceType": "Condition",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "E11", "display": "Type 2 diabetes mellitus"}]},
                    "subject": {"reference": "Patient/HN-0001"},
                },
            },
            "MedicationRequest": {
                "summary": "POST /fhir/MedicationRequest",
                "value": {
                    "resourceType": "MedicationRequest",
                    "status": "active",
                    "intent": "order",
                    "medication": {"concept": {"coding": [{"system": "http://www.whocc.no/atc", "code": "A10BA02", "display": "Metformin"}]}},
                    "subject": {"reference": "Patient/HN-0001"},
                    "dosageInstruction": [{"text": "500 mg twice daily"}],
                },
            },
            "ServiceRequest": {
                "summary": "POST /fhir/ServiceRequest",
                "value": {
                    "resourceType": "ServiceRequest",
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "code": {"coding": [{"system": "urn:his-b:order-codes", "code": "CHEM-001", "display": "Comprehensive Metabolic Panel"}]},
                    "subject": {"reference": "Patient/HN-0001"},
                },
            },
        },
    ),
    doctor: str = Depends(verify_token),
) -> JSONResponse:
    import json
    return await _proxy("POST", path, doctor, {}, json.dumps(body).encode())


# ─── PUT ──────────────────────────────────────────────────────────────────────

@router.put(
    "/fhir/{path:path}",
    summary="PUT — แก้ไข FHIR resource",
    operation_id="fhir_proxy_put",
    description="""
แก้ไข FHIR resource ที่มีอยู่แล้วผ่าน Gateway → HIS B

### ตัวอย่าง path

| path | ความหมาย |
|------|-----------|
| `Patient/HN-0001` | แก้ไขข้อมูลผู้ป่วย HN-0001 |
| `Observation/1` | แก้ไขผลแลบ ID=1 |
| `ServiceRequest/2` | แก้ไขคำสั่งแพทย์ ID=2 |

### Request Body — PUT /fhir/Patient/HN-0001
```json
{
  "resourceType": "Patient",
  "id": "HN-0001",
  "name": [{"family": "ใจดีมาก", "given": ["สมชาย"]}],
  "gender": "male",
  "birthDate": "1980-05-15",
  "telecom": [{"system": "phone", "value": "081-999-9999"}]
}
```

### Request Body — PUT /fhir/ServiceRequest/2
```json
{
  "resourceType": "ServiceRequest",
  "status": "completed",
  "intent": "order",
  "priority": "routine",
  "code": {"coding": [{"system": "urn:his-b:order-codes", "code": "RENAL-001", "display": "Renal Function Panel"}]},
  "subject": {"reference": "Patient/HN-0001"}
}
```
""",
)
async def fhir_put(
    request: Request,
    path: str,
    body: dict = Body(
        ...,
        openapi_examples={
            "Patient": {
                "summary": "PUT /fhir/Patient/HN-0001",
                "value": {
                    "resourceType": "Patient",
                    "id": "HN-0001",
                    "name": [{"family": "ใจดีมาก", "given": ["สมชาย"]}],
                    "gender": "male",
                    "birthDate": "1980-05-15",
                    "telecom": [{"system": "phone", "value": "081-999-9999"}],
                },
            },
            "ServiceRequest": {
                "summary": "PUT /fhir/ServiceRequest/2",
                "value": {
                    "resourceType": "ServiceRequest",
                    "status": "completed",
                    "intent": "order",
                    "priority": "routine",
                    "code": {"coding": [{"system": "urn:his-b:order-codes", "code": "RENAL-001", "display": "Renal Function Panel"}]},
                    "subject": {"reference": "Patient/HN-0001"},
                },
            },
        },
    ),
    doctor: str = Depends(verify_token),
) -> JSONResponse:
    import json
    return await _proxy("PUT", path, doctor, {}, json.dumps(body).encode())


# ─── DELETE ───────────────────────────────────────────────────────────────────

@router.delete(
    "/fhir/{path:path}",
    summary="DELETE — ลบ FHIR resource",
    operation_id="fhir_proxy_delete",
    description="""
ลบ FHIR resource ผ่าน Gateway → HIS B

### ตัวอย่าง path

| path | ความหมาย |
|------|-----------|
| `Patient/HN-0099` | ลบผู้ป่วย HN-0099 |
| `Observation/5` | ลบผลแลบ ID=5 |
| `ServiceRequest/3` | ลบคำสั่งแพทย์ ID=3 |

> ⚠️ การลบ Patient จะลบ Observations และ ServiceRequests ที่เกี่ยวข้องด้วย (CASCADE)
""",
)
async def fhir_delete(
    request: Request,
    path: str,
    doctor: str = Depends(verify_token),
) -> JSONResponse:
    return await _proxy("DELETE", path, doctor, dict(request.query_params))
