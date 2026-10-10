"""
EduNexus AI — Integration Tests for Flask REST API Endpoints
Tests health, students, activities, student dashboard, faculty overview,
submissions, analyze, authentication compatibility, and template views.
"""

import pytest
from app import app


@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ==========================================
# 1. Health & Status
# ==========================================

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "EduNexus AI Backend"
    assert "database" in data
    assert "provider" in data["database"]
    assert "connected" in data["database"]


# ==========================================
# 2. Students & Activities
# ==========================================

def test_get_students(client):
    response = client.get("/api/students")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] >= 4
    assert len(data["data"]) >= 4
    student_names = [s["name"] for s in data["data"]]
    assert "Aanya Patel" in student_names
    assert "Rohan Shah" in student_names


def test_get_activities(client):
    response = client.get("/api/activities")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] >= 6
    assert len(data["data"]) >= 6
    topics = {a["topic"] for a in data["data"]}
    assert "Arrays" in topics
    assert "Recursion" in topics


def test_create_activity_success(client):
    payload = {
        "title": "Recursion Mastery Assessment",
        "topic": "Recursion",
        "activity_type": "Quiz",
        "max_score": 100
    }
    response = client.post("/api/activities", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["title"] == "Recursion Mastery Assessment"
    assert data["data"]["topic"] == "Recursion"


def test_create_activity_missing_title(client):
    payload = {
        "title": "",
        "topic": "Arrays"
    }
    response = client.post("/api/activities", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "'title' is required" in data["error"]


def test_create_activity_invalid_topic(client):
    payload = {
        "title": "Quantum Physics Assessment",
        "topic": "Quantum Computing",
        "max_score": 100
    }
    response = client.post("/api/activities", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "Invalid topic" in data["error"]


def test_create_activity_invalid_score(client):
    payload = {
        "title": "Valid Quiz",
        "topic": "Stacks",
        "max_score": -10
    }
    response = client.post("/api/activities", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "positive number" in data["error"]


# ==========================================
# 3. Student Dashboard
# ==========================================

def test_get_student_dashboard_success(client):
    response = client.get("/api/student/1/dashboard")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    student_data = data["data"]

    # Profile verification
    assert student_data["profile"]["id"] == 1
    assert student_data["profile"]["name"] == "Aanya Patel"
    assert student_data["profile"]["course"] == "Data Structures"

    # Metrics
    assert "overall_score" in student_data["metrics"]
    assert "completion_rate" in student_data["metrics"]

    # Topics and recommendations
    assert isinstance(student_data["topic_scores"], list)
    assert len(student_data["topic_scores"]) == 5

    # Check recommendation schema adherence
    recs = student_data["recommendations"]
    assert isinstance(recs, list)
    for r in recs:
        assert "topic" in r
        assert "score" in r
        assert "evidence" in r
        assert "recommended_action" in r
        assert "resource" in r
        assert "priority" in r


def test_get_student_dashboard_not_found(client):
    response = client.get("/api/student/9999/dashboard")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


# ==========================================
# 4. Faculty Overview
# ==========================================

def test_get_faculty_overview(client):
    response = client.get("/api/faculty/overview")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    faculty_data = data["data"]

    assert faculty_data["course"] == "Data Structures"
    assert faculty_data["enrolled_count"] >= 4
    assert faculty_data["class_average"] > 0
    assert "topic_mastery_distribution" in faculty_data
    assert len(faculty_data["topic_mastery_distribution"]) == 5
    assert "at_risk_students" in faculty_data
    for student in faculty_data["at_risk_students"]:
        assert "suggested_intervention" in student
        assert "weak_topics_count" in student


# ==========================================
# 5. Submissions
# ==========================================

def test_create_submission_success(client):
    payload = {
        "student_id": 1,
        "activity_id": 2,
        "score": 92.5,
        "is_late": False
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["student_id"] == 1
    assert data["data"]["score"] == 92.5


def test_create_submission_missing_fields(client):
    payload = {
        "student_id": 1,
        "score": 80
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "Missing required fields" in data["error"]


def test_create_submission_invalid_score_range(client):
    payload = {
        "student_id": 1,
        "activity_id": 1,
        "score": 150
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "between 0 and 100" in data["error"]


def test_create_submission_student_not_found(client):
    payload = {
        "student_id": 9999,
        "activity_id": 1,
        "score": 75
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "Student ID '9999' does not exist" in data["error"]


def test_create_submission_activity_not_found(client):
    payload = {
        "student_id": 1,
        "activity_id": 9999,
        "score": 75
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "Activity ID '9999' does not exist" in data["error"]


# ==========================================
# 6. Analyze Endpoint
# ==========================================

def test_analyze_by_student_id(client):
    payload = {"student_id": 1}
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "overall_score" in data["data"]
    assert "weak_topics" in data["data"]
    assert "recommendations" in data["data"]


def test_analyze_by_custom_submissions(client):
    payload = {
        "submissions": [
            {"topic": "Queues", "score": 42.0, "is_late": True, "activity_title": "Queue Quiz"},
            {"topic": "Queues", "score": 45.0, "is_late": False, "activity_title": "Queue Lab"},
            {"topic": "Arrays", "score": 88.0, "is_late": False, "activity_title": "Array Test"}
        ]
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    weak = data["data"]["weak_topics"]
    assert len(weak) == 1
    assert weak[0]["topic"] == "Queues"
    assert len(data["data"]["recommendations"]) >= 1


def test_analyze_missing_input(client):
    response = client.post("/api/analyze", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "Must provide either 'student_id' or 'submissions'" in data["error"]


# ==========================================
# 7. Auth Compatibility
# ==========================================

def test_auth_login_student(client):
    payload = {"email": "aanya.patel@example.com", "password": "Password123!"}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["role"] == "student"


def test_auth_login_faculty(client):
    payload = {"email": "faculty.smith@example.com", "password": "Password123!"}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["role"] == "faculty"


def test_auth_login_missing_credentials(client):
    response = client.post("/auth/login", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_auth_register_student(client):
    payload = {
        "fullName": "New Student",
        "email": "new.student@example.com",
        "password": "Password123!",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["role"] == "student"


def test_auth_register_admin_rejected(client):
    payload = {
        "fullName": "Admin Attempter",
        "email": "admin@example.com",
        "password": "Password123!",
        "role": "admin"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 403
    data = response.get_json()
    assert data["success"] is False
    assert "Admin registration is not permitted" in data["message"]


def test_auth_register_short_password(client):
    payload = {
        "fullName": "Short Pass",
        "email": "short@example.com",
        "password": "short",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "at least 8 characters" in data["message"]


def test_auth_me(client):
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "fullName" in data["data"]


def test_auth_logout(client):
    response = client.post("/auth/logout")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


# ==========================================
# 8. Template View Routes
# ==========================================

def test_view_routes(client):
    views = [
        "/",
        "/login",
        "/register",
        "/student-dashboard",
        "/faculty-dashboard",
        "/admin-dashboard"
    ]
    for path in views:
        res = client.get(path)
        assert res.status_code == 200, f"Failed for path: {path}"


def test_api_404_handler(client):
    res = client.get("/api/unknown_endpoint")
    assert res.status_code == 404
    data = res.get_json()
    assert data["success"] is False
    assert "Endpoint not found" in data["error"]
