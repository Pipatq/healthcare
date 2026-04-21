[ User: Doctor A ]
       |
       | (HTTPS/REST)
       v
+-------------------------+
|         HIS A           |
|  (Requesting System)    |
|  - Web Portal           |
|  - FHIR Client Layer    |
+----------+--------------+
           |
           | [ Request: Patient ID / FHIR Resource ]
           | (JSON Over HTTPS)
           v
+-------------------------+
|   Interoperability      |
|        Server           | <--- FHIR API Gateway / Router
| (FHIR 8.2.0 Validation) |
+----------+--------------+
           |
           | [ Forwarded Request ]
           v
+-------------------------+          +-----------------------+
|         HIS B           |          |      HIS B DB         |
|   (Resource Provider)   |          |    (Legacy SQL/NoSQL) |
|                         |          |                       |
|  +-------------------+  |          |  - Patient Table      |
|  |   FHIR Facade     |  | (Query)  |  - Observation Table  |
|  |  (FastAPI Micro)  +------------>|  - Diagnostic Table   |
|  +---------+---------+  |          |                       |
|            ^            |          +-----------+-----------+
|            |            |                      |
|            +------------+----------------------+
|             (Data Mapping to FHIR Resource)
+-------------------------+




Flow การทำงานได้ดังนี้:

Doctor A: แพทย์ผู้ใช้งานระบบอยู่ที่ฝั่ง HIS A ต้องการดูข้อมูลคนไข้ (ที่อาจจะประวัติอยู่ที่ HIS B)

HIS A (Hospital Information System A): ระบบต้นทาง มี Database ของตัวเอง และมี Facade Component ทำหน้าที่ดึงข้อมูลจาก DB ภายในมาแปลง (Transform) ให้อยู่ในรูปแบบ FHIR Resource

FHIR Server / Interoperability Layer: เป็นตัวกลางรับ Request (เป็น JSON format) จาก HIS A แล้ว Routing/Forward ไปยัง HIS B

HIS B: ระบบปลายทาง มี Facade Component รับ FHIR Request เข้ามา แปลงกลับเป็น Query ดึงข้อมูลจาก DB ตัวเอง แล้วตอบกลับ (Response) เป็น FHIR Resource (เช่น ข้อมูล Patient) กลับไปให้ HIS A


ฺBacklog :

Epic 1: HIS B FHIR Facade Microservice (Data Provider)
เป้าหมาย: สร้างตัวครอบระบบ HIS B เพื่อเปิด API ให้ดึงข้อมูลและแปลงเป็น FHIR Standard

Story 1.1: As a Backend Engineer, I want to scaffold a FastAPI application so that we have a lightweight web server for the Facade.

Task: Setup FastAPI project structure.

Task: Create Dockerfile (Python 3.11-slim) and docker-compose.yml for local dev.

Story 1.2: As a Backend Engineer, I want to connect the Facade to the HIS B Legacy Database so that I can query raw patient data.

Task: Implement DB Connection Pool (e.g., SQLAlchemy/asyncpg).

Task: Write query logic to fetch Patient data by ID/HN.

Story 1.3: As a Data Engineer, I want to map legacy database fields to FHIR Patient Resource (v8.2.0) so that the response complies with HL7 standards.

Task: Implement Pydantic validation using fhir.resources.patient.

Task: Handle data anomalies (e.g., Missing fields, Type casting errors) gracefully.

Task: Write Unit Tests for the mapping logic.

Epic 2: FHIR Gateway & Routing Layer (The Middleman)
เป้าหมาย: สร้างตัวกลางตามวงกลมตรงกลางรูป เพื่อทำหน้าที่รับ-ส่ง Request

Story 2.1: As a Platform Engineer, I want to set up an API Gateway/Router to forward requests from HIS A to HIS B.

Task: Setup Nginx, Kong, หรือพัฒนา Lightweight Router ด้วย Python (ขึ้นอยู่กับ Stack องค์กร).

Task: Configure Routing rules (e.g., /fhir/Patient/* -> Route to HIS B Facade).

Task: Implement API Key authentication หรือ mTLS ระหว่าง Services.

Epic 3: HIS A Integration (Data Consumer)
เป้าหมาย: ให้ระบบต้นทางสามารถยิง Request และแสดงผลได้

Story 3.1: As a HIS A Developer, I want to send a RESTful GET request to the FHIR Gateway so that I can request patient data.

Task: Implement HTTP Client logic in HIS A.

Task: Parse incoming FHIR JSON response.

Story 3.2: As a Doctor A (End User), I want to view the fetched patient data on my HIS A interface so that I can make clinical decisions.

Task: Bind parsed FHIR JSON to HIS A Frontend UI.

Epic 4: SRE & DevOps (Non-Functional Requirements)
เป้าหมาย: ทำให้ระบบพร้อมขึ้น Production อย่างมั่นคง (ไม่ Over-engineer แต่ต้อง Monitor ได้)

Story 4.1: As a DevOps Engineer, I want to implement centralized logging and metrics so that I can monitor the mapping success rate and latency.

Task: Add structured JSON logging (e.g., Loguru) to the Python Microservice.

Task: Expose /metrics endpoint for Prometheus (Track Error 500s from Data Mapping).

Story 4.2: As a DevOps Engineer, I want to set up a CI/CD pipeline to automatically test and build the Docker image.

Task: Write CI script to run Python Linter and Pytest.

Task: Build and push Docker image to Container Registry.



1. Requirements Analysis
Business Requirements (ฝั่งผู้ใช้งาน):

แพทย์ (Doctor A) ที่ระบบ HIS A ต้องสามารถดึงดูข้อมูลคนไข้ (Patient) หรือผลการรักษาข้ามโรงพยาบาลที่อยู่ในระบบ HIS B ได้

ระบบต้องตอบสนองได้เร็ว (Synchronous Request/Response)

Technical Requirements (ฝั่งระบบ):

HIS B Facade: ต้องมี Microservice ที่ครอบ HIS B เดิมไว้ ทำหน้าที่รับ Request และแปลงข้อมูลจาก Legacy Database ให้เป็นมาตรฐาน HL7 FHIR (ใช้ Python fhir.resources version 8.2.0)

Gateway Layer: ต้องมีตัวกลาง (FHIR Server / Router) คอยรับ Request จาก HIS A และ Forward ไปยัง HIS B ที่ถูกต้อง (Routing)

Data Format: คุยกันด้วย JSON payload

Infrastructure: รันบน Docker Container แบบ Stateless เพื่อการ Scale และ Maintain ที่ง่าย










http://localhost/patients  หน้าแสดงรายชื่อผู้ป่วยทั้งหมด — UI สำหรับหมอ             
http://localhost/observations  	หน้าแสดงผลแลบ (Lab results)
http://localhost/service-requests   หน้าแสดงคำสั่งแพทย์ (Lab orders)


http://localhost:8000/docs HIS A Backend — ระบบโรงพยาบาล A (ฝั่งหมอ) 


http://localhost:8001/docs  FHIR Gateway — ตัวกลางที่รับคำขอจาก HIS A แล้วส่งต่อไป HIS B


http://localhost:8002/docs  HIS B Facade — ระบบโรงพยาบาล B (เจ้าของข้อมูลจริง)