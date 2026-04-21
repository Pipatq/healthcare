"""
HIS A – FHIR Proxy routes.

Doctor-facing endpoints: JWT-protected. Each request is forwarded to the
FHIR Gateway which routes it to HIS B, adding the inter-service API key.
"""

import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
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


@router.api_route(
    "/fhir/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    summary="FHIR proxy – forwards to FHIR Gateway → HIS B",
    description="""
Forward FHIR R5 request ผ่าน Gateway ไปยัง HIS B. ต้องใส่ **JWT Bearer token** (จาก POST /auth/login)

> **Authorization:** กด **Authorize** แล้วใส่ token ในรูปแบบ `Bearer <token>`

---

### GET — ดึงข้อมูล (ไม่ต้องใส่ body)

| path | ความหมาย |
|---|---|
| `Patient` | ดูผู้ป่วยทั้งหมด |
| `Patient/HN-0001` | ดูผู้ป่วย สมชาย ใจดี |
| `Patient/HN-0002` | ดูผู้ป่วย สมหญิง รักดี |
| `Observation` | ดูผลแลบทั้งหมด |
| `Observation?patient=HN-0001` | ดูผลแลบของ HN-0001 |
| `ServiceRequest` | ดูคำสั่งแพทย์ทั้งหมด |
| `ServiceRequest?patient=HN-0001` | ดูคำสั่งแพทย์ของ HN-0001 |

---

### POST — สร้างข้อมูลใหม่ (ต้องใส่ JSON body ใน Request body)

| path | ความหมาย |
|---|---|
| `Patient` | สร้างผู้ป่วยใหม่ |
| `Observation` | บันทึกผลแลบใหม่ |
| `ServiceRequest` | สร้างคำสั่งแพทย์ใหม่ |

**ตัวอย่าง body สำหรับ POST /fhir/Patient:**
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
""",
)
async def proxy_to_gateway(
    request: Request,
    path: str,
    doctor: str = Depends(verify_token),
) -> JSONResponse:
    target_url = f"/fhir/{path}"
    method = request.method
    body = await request.body()
    params = dict(request.query_params)

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
