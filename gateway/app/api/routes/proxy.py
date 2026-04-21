"""
FHIR Gateway Proxy Router.

Receives FHIR requests from HIS A, validates the caller's API key,
then forwards the request to the HIS B Facade, injecting HIS B's API key.
"""

import time
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.deps import verify_api_key
from app.core.config import settings

router = APIRouter(tags=["fhir-gateway"])

# Reusable async HTTP client (connection pooling)
_http_client: httpx.AsyncClient | None = None

_AUTH_NOTE = (
    "> **API Key (X-API-Key):** `gateway-secret-key`"
    " — กด **Authorize** (รูปกุญแจ) แล้วใส่ key ก่อนกด Execute"
)

_GET_EXAMPLES = """
| path | ความหมาย |
|---|---|
| `Patient` | ดูผู้ป่วยทั้งหมด |
| `Patient/HN-0001` | ดูผู้ป่วย สมชาย ใจดี |
| `Patient/HN-0002` | ดูผู้ป่วย สมหญิง รักดี |
| `Patient/HN-0003` | ดูผู้ป่วย วิชัย แสงทอง |
| `Observation` | ดูผลแลบทั้งหมด |
| `Observation?patient=HN-0001` | ดูผลแลบของ HN-0001 |
| `Observation?patient=HN-0002` | ดูผลแลบของ HN-0002 |
| `ServiceRequest` | ดูคำสั่งแพทย์ทั้งหมด |
| `ServiceRequest?patient=HN-0001` | ดูคำสั่งแพทย์ของ HN-0001 |
"""


def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized.")
    return _http_client


async def startup_client() -> None:
    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=settings.HIS_B_BASE_URL,
        timeout=settings.PROXY_TIMEOUT,
        headers={"X-API-Key": settings.HIS_B_API_KEY},
    )


async def shutdown_client() -> None:
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


async def _forward(request: Request, path: str, method: str, body: bytes | None = None) -> JSONResponse:
    target_url = f"/fhir/{path}"
    params = dict(request.query_params)
    forward_headers: dict[str, str] = {"Content-Type": "application/json"}

    t0 = time.monotonic()
    try:
        client = get_http_client()
        response = await client.request(
            method=method,
            url=target_url,
            params=params,
            content=body or None,
            headers=forward_headers,
        )
    except httpx.TimeoutException:
        logger.error("Timeout forwarding {} {} to HIS B", method, target_url)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="HIS B Facade did not respond in time.",
        )
    except httpx.RequestError as exc:
        logger.error("Network error forwarding to HIS B: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cannot reach HIS B Facade.",
        )

    latency_ms = round((time.monotonic() - t0) * 1000)
    logger.info(
        "PROXY {} /fhir/{} → HIS B | status={} latency={}ms",
        method, path, response.status_code, latency_ms,
    )

    try:
        payload: Any = response.json()
    except Exception:
        payload = {"raw": response.text}

    return JSONResponse(content=payload, status_code=response.status_code)


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------

@router.get(
    "/fhir/{path:path}",
    summary="GET — ดึงข้อมูล FHIR จาก HIS B",
    description=f"""
ดึงข้อมูล FHIR resource จาก HIS B ไม่ต้องใส่ body

{_AUTH_NOTE}

{_GET_EXAMPLES}
""",
)
async def proxy_get(
    request: Request,
    path: str,
    _caller: str = Depends(verify_api_key),
) -> JSONResponse:
    return await _forward(request, path, "GET")


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------

@router.post(
    "/fhir/{path:path}",
    summary="POST — สร้างข้อมูล FHIR ใหม่ใน HIS B",
    description=f"""
สร้าง FHIR resource ใหม่ใน HIS B ต้องใส่ JSON body ใน **Request body** ด้านล่าง

{_AUTH_NOTE}

| path | ความหมาย |
|---|---|
| `Patient` | สร้างผู้ป่วยใหม่ |
| `Observation` | บันทึกผลแลบใหม่ |
| `ServiceRequest` | สร้างคำสั่งแพทย์ใหม่ |

**ตัวอย่าง body สำหรับ `Patient`:**
```json
{{
  "resourceType": "Patient",
  "id": "HN-0099",
  "identifier": [{{"system": "urn:his-b:hn", "value": "HN-0099"}}],
  "name": [{{"family": "ทดสอบ", "given": ["ผู้ป่วย"]}}],
  "gender": "male",
  "birthDate": "1990-01-01"
}}
```

**ตัวอย่าง body สำหรับ `Observation`:**
```json
{{
  "resourceType": "Observation",
  "status": "final",
  "code": {{"coding": [{{"system": "http://loinc.org", "code": "718-7", "display": "Hemoglobin"}}]}},
  "subject": {{"reference": "Patient/HN-0001"}},
  "issued": "2026-04-21T10:00:00+07:00",
  "valueQuantity": {{"value": 13.5, "unit": "g/dL", "system": "http://unitsofmeasure.org", "code": "g/dL"}}
}}
```
""",
)
async def proxy_post(
    request: Request,
    path: str,
    body: dict = Body(
        ...,
        openapi_examples={
            "patient": {
                "summary": "สร้างผู้ป่วยใหม่ (path = Patient)",
                "value": {
                    "resourceType": "Patient",
                    "id": "HN-0099",
                    "identifier": [{"system": "urn:his-b:hn", "value": "HN-0099"}],
                    "name": [{"family": "ทดสอบ", "given": ["ผู้ป่วย"]}],
                    "gender": "male",
                    "birthDate": "1990-01-01",
                },
            },
            "observation": {
                "summary": "บันทึกผลแลบใหม่ (path = Observation)",
                "value": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "718-7", "display": "Hemoglobin"}]},
                    "subject": {"reference": "Patient/HN-0001"},
                    "issued": "2026-04-21T10:00:00+07:00",
                    "valueQuantity": {"value": 13.5, "unit": "g/dL", "system": "http://unitsofmeasure.org", "code": "g/dL"},
                },
            },
        },
    ),
    _caller: str = Depends(verify_api_key),
) -> JSONResponse:
    import json
    return await _forward(request, path, "POST", json.dumps(body).encode())


# ---------------------------------------------------------------------------
# PUT
# ---------------------------------------------------------------------------

@router.put(
    "/fhir/{path:path}",
    summary="PUT — อัปเดตข้อมูล FHIR ใน HIS B",
    description=f"""
อัปเดต FHIR resource ที่มีอยู่แล้วใน HIS B

{_AUTH_NOTE}

| path | ความหมาย |
|---|---|
| `Patient/HN-0001` | อัปเดตข้อมูลผู้ป่วย HN-0001 |

ใส่ FHIR resource ทั้งหมดใน **Request body** (เหมือน POST แต่ระบุ id ที่ต้องการแก้)
""",
)
async def proxy_put(
    request: Request,
    path: str,
    body: dict = Body(...),
    _caller: str = Depends(verify_api_key),
) -> JSONResponse:
    import json
    return await _forward(request, path, "PUT", json.dumps(body).encode())


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------

@router.patch(
    "/fhir/{path:path}",
    summary="PATCH — แก้ไขบางส่วนของ FHIR resource",
    description=f"""
แก้ไขบางฟิลด์ของ FHIR resource ใน HIS B

{_AUTH_NOTE}

ใส่เฉพาะฟิลด์ที่ต้องการแก้ใน **Request body**
""",
)
async def proxy_patch(
    request: Request,
    path: str,
    body: dict = Body(...),
    _caller: str = Depends(verify_api_key),
) -> JSONResponse:
    import json
    return await _forward(request, path, "PATCH", json.dumps(body).encode())


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@router.delete(
    "/fhir/{path:path}",
    summary="DELETE — ลบ FHIR resource ใน HIS B",
    description=f"""
ลบ FHIR resource ใน HIS B (ไม่ต้องใส่ body)

{_AUTH_NOTE}

| path | ความหมาย |
|---|---|
| `Patient/HN-0099` | ลบผู้ป่วย HN-0099 |
| `Observation/5` | ลบผลแลบ id=5 |
""",
)
async def proxy_delete(
    request: Request,
    path: str,
    _caller: str = Depends(verify_api_key),
) -> JSONResponse:
    return await _forward(request, path, "DELETE")

