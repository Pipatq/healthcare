# คู่มือการใช้งาน HIS-to-HIS Interoperability

## Services และ URL

| Service | URL | ใช้ทำอะไร |
|---|---|---|
| หน้าเว็บ (Frontend) | http://localhost | UI สำหรับหมอ |
| HIS A Backend API | http://localhost:8000/docs | API ของหมอ (JWT) |
| FHIR Gateway API | http://localhost:8001/docs | ตัวกลาง routing |
| HIS B Facade API | http://localhost:8002/docs | เจ้าของข้อมูลจริง |

---

## เริ่มต้นระบบ

```bash
docker compose up --build -d
```

หยุดระบบ (เก็บข้อมูลไว้):
```bash
docker compose down
```

หยุดระบบ + ลบข้อมูลทั้งหมด:
```bash
docker compose down -v
```

---

## Flow การทำงาน

```
หมอ (Browser)
  ↓  login ด้วย username/password
HIS A :8000  →  ออก JWT Token
  ↓  ส่ง JWT ทุก request
HIS A :8000  →  ตรวจสอบ JWT แล้วส่งต่อ
  ↓  X-API-Key: gateway-secret-key
Gateway :8001  →  ตรวจสอบ API Key แล้วส่งต่อ
  ↓  X-API-Key: his-b-secret-key
HIS B :8002  →  ดึง/บันทึกข้อมูลจาก Database
```

---

## วิธีใช้งานหน้าเว็บ

1. เปิด **http://localhost**
2. Login ด้วย account ทดสอบ:
   - Username: ``
   - Password: ``
3. เลือกดูหน้า Patients / Observations / Service Requests

---

## วิธีใช้ Swagger (ทดสอบ API โดยตรง)

### HIS B — http://localhost:8002/docs
> ทดสอบข้อมูลโดยตรง ไม่ผ่านระบบ HIS A

1. กดปุ่ม **Authorize** → ใส่ `his-b-secret-key`
2. เลือก endpoint ที่ต้องการ

| ต้องการดู | ใช้ endpoint |
|---|---|
| ผู้ป่วยทั้งหมด | GET `/Patient` |
| ผู้ป่วยรายคน | GET `/Patient/{HN}` เช่น `HN-0001` |
| ผลแลบ | GET `/Observation?patient=HN-0001` |
| คำสั่งแพทย์ | GET `/ServiceRequest?patient=HN-0001` |

---

### Gateway — http://localhost:8001/docs
> จำลอง HIS A ส่ง request มาที่ Gateway

1. กดปุ่ม **Authorize** → ใส่ `gateway-secret-key`
2. เลือก method ที่ต้องการ (GET/POST/PUT/DELETE)
3. ใส่ `path` ตามตาราง:

| path | ความหมาย |
|---|---|
| `Patient` | ผู้ป่วยทั้งหมด |
| `Patient/HN-0001` | ผู้ป่วยรายคน |
| `Observation?patient=HN-0001` | ผลแลบ |
| `ServiceRequest` | คำสั่งแพทย์ทั้งหมด |

---

### HIS A — http://localhost:8000/docs
> ทดสอบในฐานะหมอ (ต้อง login ก่อน)

1. POST `/auth/login` → ใส่ `{ "username": "admin", "password": "admin1234" }`
2. คัดลอก `access_token` ที่ได้
3. กดปุ่ม **Authorize** → ใส่ `Bearer <token>`
4. ใช้ endpoint `/fhir/{path}` เหมือน Gateway

---

## ข้อมูลทดสอบที่มีอยู่ใน Database

| HN | ชื่อ | เพศ |
|---|---|---|
| HN-0001 | สมชาย ใจดี | ชาย |
| HN-0002 | สมหญิง รักดี | หญิง |
| HN-0003 | วิชัย แสงทอง | ชาย |
| HN-0004 | นภาพร จันทร์งาม | หญิง |
| HN-0005 | ประยุทธ์ สุขใจ | ชาย |

ผลแลบ (Observation ID): `1`–`10`  
คำสั่งแพทย์ (ServiceRequest ID): `1`–`7`

---

## API Keys สรุป

| ใช้ที่ | Header | ค่า |
|---|---|---|
| HIS A → Gateway | `X-API-Key` | `gateway-secret-key` |
| Gateway → HIS B | `X-API-Key` | `his-b-secret-key` |
| HIS A Doctor | `Authorization` | `Bearer <jwt_token>` |
