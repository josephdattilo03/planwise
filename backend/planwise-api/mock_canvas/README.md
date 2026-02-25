# Mock Canvas API (Local Dev)

This is a lightweight mock of a small subset of the Canvas LMS API for local development and testing.

## Run

From the `backend/planwise-api` directory:

```bash
python3 mock_canvas/server.py
cat > mock_canvas/README.md <<'MD'
# Mock Canvas API

This folder contains a lightweight mock of a subset of the Canvas LMS API used for Planwise development.

The goal is to allow backend and frontend development **without requiring a full Canvas installation**.

---

# Why This Exists

Running Canvas locally is:

• heavy  
• slow to start  
• fragile across machines  

This mock provides predictable API responses that match the structure of the real Canvas API.

The real Canvas instance was used to capture the JSON structure used here.

---

# Quick Start

From inside:

backend/planwise-api

run:

python3 mock_canvas/server.py

You should see:

Mock Canvas listening on http://127.0.0.1:5001

---

# Base URL

http://127.0.0.1:5001

---

# Authentication

Authentication is **not enforced** in this mock.

Requests may include:

Authorization: Bearer anything

but it is ignored.

This keeps development simple.

---

# Implemented Endpoints

These mirror the Canvas API routes used by the Planwise backend.

---

## Health Check

GET /health

Example:

curl http://127.0.0.1:5001/health

Response:

{
  "status": "ok"
}

---

# Courses

Return all courses.

GET /api/v1/courses

Example:

curl http://127.0.0.1:5001/api/v1/courses

Example Response:

[
  {
    "id": 4,
    "name": "Biology 101",
    "course_code": "BIO101"
  }
]

---

# Course Detail

GET /api/v1/courses/:id

Example:

curl http://127.0.0.1:5001/api/v1/courses/4

---

# Assignments for a Course

GET /api/v1/courses/:id/assignments

Example:

curl http://127.0.0.1:5001/api/v1/courses/4/assignments

Example Response:

[
  {
    "id": 101,
    "name": "Bio Lab 1",
    "due_at": "2026-03-02T23:59:00Z",
    "published": true
  }
]

---

# Single Assignment

GET /api/v1/courses/:course_id/assignments/:assignment_id

Example:

curl http://127.0.0.1:5001/api/v1/courses/4/assignments/101

---

# Fixture Data

All data returned by this service comes from JSON files located in:

mock_canvas/data/

Files include:

courses.json
assignments_4.json
assignments_5.json
assignments_6.json

You can modify these files to simulate different scenarios.

Example changes:

• upcoming assignments  
• missing due dates  
• unpublished assignments  
• new courses

No server restart is required unless new endpoints are added.

---

# Intended Development Workflow

Backend:

calls mock Canvas

Frontend:

calls backend

Architecture during development:

Frontend
   ↓
Planwise API
   ↓
Mock Canvas

Later this can be replaced with the real Canvas API.

---

# Future Improvements

Possible additions if needed:

• modules endpoint  
• planner items endpoint  
• submissions endpoint  
• pagination support  
• authentication simulation

---

# Contact

If something breaks or you need another endpoint, update the fixtures or server in this folder.
