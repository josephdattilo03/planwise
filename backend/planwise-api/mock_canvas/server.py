#!/usr/bin/env python3
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        # Health check
        if path == "/health":
            return self._send_json({"status": "ok"})

        # User identity (common first call in Canvas integrations)
        if path == "/api/v1/users/self":
            return self._send_json(load_json("users_self.json"))

        # Courses index
        if path == "/api/v1/courses":
            return self._send_json(load_json("courses.json"))

        # Course detail
        m = re.match(r"^/api/v1/courses/(\d+)$", path)
        if m:
            course_id = int(m.group(1))
            courses = load_json("courses.json")
            course = next((c for c in courses if int(c.get("id")) == course_id), None)
            if course is None:
                return self._send_json(
                    {"errors": [{"message": f"Course {course_id} not found"}]},
                    status=404,
                )
            return self._send_json(course)

        # Assignments list for a course
        m = re.match(r"^/api/v1/courses/(\d+)/assignments$", path)
        if m:
            course_id = m.group(1)
            filename = f"assignments_{course_id}.json"
            try:
                return self._send_json(load_json(filename))
            except FileNotFoundError:
                return self._send_json(
                    {"errors": [{"message": f"No fixture for course {course_id}"}]},
                    status=404,
                )

        # Single assignment detail
        m = re.match(r"^/api/v1/courses/(\d+)/assignments/(\d+)$", path)
        if m:
            course_id, assignment_id = m.group(1), int(m.group(2))
            filename = f"assignments_{course_id}.json"
            try:
                assignments = load_json(filename)
            except FileNotFoundError:
                return self._send_json(
                    {"errors": [{"message": f"No fixture for course {course_id}"}]},
                    status=404,
                )
            assignment = next((a for a in assignments if int(a.get("id")) == assignment_id), None)
            if assignment is None:
                return self._send_json(
                    {"errors": [{"message": f"Assignment {assignment_id} not found"}]},
                    status=404,
                )
            return self._send_json(assignment)

        # Planner items (aggregated upcoming work)
        if path == "/api/v1/planner/items":
            return self._send_json(load_json("planner_items.json"))

        return self._send_json(
            {"errors": [{"message": "Not found", "path": path}]},
            status=404,
        )

def main():
    host = os.environ.get("MOCK_CANVAS_HOST", "127.0.0.1")
    port = int(os.environ.get("MOCK_CANVAS_PORT", "5001"))
    server = HTTPServer((host, port), Handler)
    print(f"Mock Canvas listening on http://{host}:{port}")
    print("Endpoints:")
    print("  GET /health")
    print("  GET /api/v1/users/self")
    print("  GET /api/v1/courses")
    print("  GET /api/v1/courses/{id}")
    print("  GET /api/v1/courses/{id}/assignments")
    print("  GET /api/v1/courses/{id}/assignments/{assignment_id}")
    print("  GET /api/v1/planner/items")
    server.serve_forever()

if __name__ == "__main__":
    main()
