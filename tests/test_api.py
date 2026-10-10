"""
EduNexus AI — Integration Tests for Flask REST API Endpoints
Tests health, students, activities, student dashboard, faculty overview,
submissions, analyze, authentication compatibility, and template views.
"""

import os
import pytest
from app import app


def set_session_role(client, role="student", user_id=1, email=None, name=None):
    """Helper to set an authenticated server-side Flask session for a given role."""
    default_emails = {
        "student": "aanya.demo@example.com",
        "faculty": os.getenv("FACULTY_EMAIL", "faculty@edunexus.com"),
        "admin": os.getenv("ADMIN_EMAIL", "admin@edunexus.com"),
    }
    default_names = {
        "student": "Aanya Patel",
        "faculty": "Dr. Sarah Mitchell",
        "admin": "System Administrator",
    }
    with client.session_transaction() as sess:
        sess["user"] = {
            "id": user_id,
            "fullName": name or default_names.get(role, "User"),
            "name": name or default_names.get(role, "User"),
            "email": email or default_emails.get(role, f"{role}@edunexus.com"),
            "role": role,
            "department": "Computer Science",
            "course": "Data Structures",
        }


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
    assert "diagnostics" in data["database"]
    assert "failure_category" in data["database"]["diagnostics"]
    assert "message" in data["database"]["diagnostics"]


# ==========================================
# 2. Students & Activities
# ==========================================

def test_get_students(client):
    set_session_role(client, "faculty")
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
    set_session_role(client, "student")
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
    set_session_role(client, "faculty")
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
    set_session_role(client, "faculty")
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
    set_session_role(client, "faculty")
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
    set_session_role(client, "faculty")
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
    set_session_role(client, "student", user_id=1)
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
    set_session_role(client, "student")
    response = client.get("/api/student/9999/dashboard")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


# ==========================================
# 4. Faculty Overview
# ==========================================

def test_get_faculty_overview(client):
    set_session_role(client, "faculty")
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
    set_session_role(client, "student")
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
    set_session_role(client, "student")
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
    set_session_role(client, "student")
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
    set_session_role(client, "student")
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
    set_session_role(client, "student")
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
    set_session_role(client, "student")
    payload = {"student_id": 1}
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "overall_score" in data["data"]
    assert "weak_topics" in data["data"]
    assert "recommendations" in data["data"]


def test_analyze_by_custom_submissions(client):
    set_session_role(client, "student")
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
    set_session_role(client, "student")
    response = client.post("/api/analyze", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "Must provide either 'student_id' or 'submissions'" in data["error"]


# ==========================================
# 7. Authentication & Role-Based Access Control
# ==========================================

def test_auth_login_student(client):
    reg_payload = {
        "fullName": "Aanya Student",
        "email": "aanya.patel@example.com",
        "password": "Password123!",
        "role": "student"
    }
    client.post("/auth/register", json=reg_payload)

    payload = {"email": "aanya.patel@example.com", "password": "Password123!"}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["role"] == "student"
    assert data["data"]["redirectUrl"] == "/student-dashboard"


def test_auth_login_faculty(client):
    faculty_email = os.getenv("FACULTY_EMAIL", "faculty@edunexus.com")
    faculty_password = os.getenv("FACULTY_PASSWORD")
    assert faculty_password, "FACULTY_PASSWORD must be configured in .env"

    payload = {"email": faculty_email, "password": faculty_password}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["role"] == "faculty"
    assert data["data"]["redirectUrl"] == "/faculty-dashboard"


def test_auth_login_admin(client):
    admin_email = os.getenv("ADMIN_EMAIL", "admin@edunexus.com")
    admin_password = os.getenv("ADMIN_PASSWORD")
    assert admin_password, "ADMIN_PASSWORD must be configured in .env"

    payload = {"email": admin_email, "password": admin_password}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["role"] == "admin"
    assert data["data"]["redirectUrl"] == "/admin-dashboard"


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
    assert data["data"]["redirectUrl"] == "/login"
    user = data["data"]["user"]
    assert user["role"] == "student"
    assert user["table"] == "students"
    assert user["email"] == "new.student@example.com"
    assert "password" not in user


def test_auth_register_duplicate_email_rejected(client):
    payload = {
        "fullName": "Duplicate Student",
        "email": "aanya.demo@example.com",
        "password": "Password123!",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    data = response.get_json()
    assert data["success"] is False
    assert "already registered" in data["message"].lower()


def test_auth_register_faculty_blocked_for_public_allowed_for_admin(client):
    payload = {
        "fullName": "Dr. Vikram Sarabhai",
        "email": "vikram.faculty@example.com",
        "password": "Password123!",
        "role": "faculty"
    }
    # Public / unauthenticated registration as faculty must be blocked (403)
    public_res = client.post("/auth/register", json=payload)
    assert public_res.status_code == 403
    assert public_res.get_json()["success"] is False

    # Student session attempting to register faculty must also be blocked (403)
    set_session_role(client, "student")
    student_res = client.post("/auth/register", json=payload)
    assert student_res.status_code == 403

    # Admin session is authorized to provision a faculty account (201)
    set_session_role(client, "admin")
    admin_res = client.post("/auth/register", json=payload)
    assert admin_res.status_code == 201
    data = admin_res.get_json()
    assert data["success"] is True
    user = data["data"]["user"]
    assert user["role"] == "faculty"
    assert user["table"] == "faculty"
    assert user["email"] == "vikram.faculty@example.com"


def test_auth_register_invalid_email_rejected(client):
    payload = {
        "fullName": "Invalid Email User",
        "email": "not-an-email",
        "password": "Password123!",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "valid institutional email" in data["message"].lower()


def test_auth_login_verifies_registered_password_hash(client):
    reg_payload = {
        "fullName": "Hash Test User",
        "email": "hashtest.student@example.com",
        "password": "StrongPassword99!",
        "role": "student"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    # Wrong password should be rejected with 401
    bad_login = client.post("/api/auth/login", json={
        "email": "hashtest.student@example.com",
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401
    assert bad_login.get_json()["success"] is False

    # Unregistered email should be rejected with 401
    unknown_login = client.post("/api/auth/login", json={
        "email": "nonexistent.account@example.com",
        "password": "StrongPassword99!"
    })
    assert unknown_login.status_code == 401

    # Correct password should succeed with 200 and return the registered user's ID
    good_login = client.post("/api/auth/login", json={
        "email": "hashtest.student@example.com",
        "password": "StrongPassword99!"
    })
    assert good_login.status_code == 200
    good_data = good_login.get_json()
    assert good_data["success"] is True
    assert good_data["data"]["user"]["fullName"] == "Hash Test User"


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
    # Unauthenticated request to /auth/me must return 401
    unauth_res = client.get("/auth/me")
    assert unauth_res.status_code == 401

    # Authenticated request returns session user
    set_session_role(client, "student")
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "fullName" in data["data"]


def test_auth_logout(client):
    set_session_role(client, "student")
    assert client.get("/student-dashboard").status_code == 200

    response = client.post("/auth/logout")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    # After logout, session is invalidated and dashboard redirects to /login
    post_logout_res = client.get("/student-dashboard")
    assert post_logout_res.status_code == 302
    assert "/login" in post_logout_res.headers["Location"]
    assert client.get("/auth/me").status_code == 401


# ==========================================
# 8. Template View Routes & RBAC Enforcement
# ==========================================

def test_view_routes(client):
    # Public routes accessible without login
    for path in ["/", "/login", "/register"]:
        res = client.get(path)
        assert res.status_code == 200, f"Failed for public path: {path}"

    # Unauthenticated dashboard requests redirect to /login
    for protected_path in ["/student-dashboard", "/faculty-dashboard", "/admin-dashboard"]:
        res = client.get(protected_path)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]

    # Each role can access only its own dashboard and gets 403 on other dashboards
    set_session_role(client, "student")
    std_dash = client.get("/student-dashboard")
    assert std_dash.status_code == 200
    assert "no-store" in std_dash.headers.get("Cache-Control", "")
    assert client.get("/faculty-dashboard").status_code == 403
    assert client.get("/admin-dashboard").status_code == 403

    set_session_role(client, "faculty")
    fac_dash = client.get("/faculty-dashboard")
    assert fac_dash.status_code == 200
    assert "no-store" in fac_dash.headers.get("Cache-Control", "")
    assert client.get("/student-dashboard").status_code == 403
    assert client.get("/admin-dashboard").status_code == 403

    set_session_role(client, "admin")
    adm_dash = client.get("/admin-dashboard")
    assert adm_dash.status_code == 200
    assert "no-store" in adm_dash.headers.get("Cache-Control", "")
    assert client.get("/student-dashboard").status_code == 403
    assert client.get("/faculty-dashboard").status_code == 403


def test_navigation_links_and_static_assets(client):
    # Verify Home page links
    home_html = client.get("/").get_data(as_text=True)
    assert 'href="/login"' in home_html
    assert 'href="/register"' in home_html
    assert 'href="/student-dashboard"' in home_html
    assert 'href="/faculty-dashboard"' in home_html
    assert 'href="/admin-dashboard"' in home_html
    assert "templates/" not in home_html

    # Verify Login page links & static URLs (email input preserved)
    login_html = client.get("/login").get_data(as_text=True)
    assert 'href="/register"' in login_html
    assert 'type="email"' in login_html
    assert 'id="loginEmail"' in login_html
    assert 'href="/static/css/auth.css"' in login_html
    assert 'src="/static/js/auth.js"' in login_html
    assert "register.html" not in login_html
    assert "../static" not in login_html

    # Verify Register page links & static URLs
    reg_html = client.get("/register").get_data(as_text=True)
    assert 'href="/login"' in reg_html
    assert 'href="/static/css/auth.css"' in reg_html
    assert 'src="/static/js/auth.js"' in reg_html

    # Verify Dashboards render for their authorized roles
    set_session_role(client, "student")
    student_html = client.get("/student-dashboard").get_data(as_text=True)
    assert 'src="/static/js/student.js"' in student_html

    set_session_role(client, "faculty")
    faculty_html = client.get("/faculty-dashboard").get_data(as_text=True)
    assert 'src="/static/js/faculty.js"' in faculty_html

    set_session_role(client, "admin")
    admin_html = client.get("/admin-dashboard").get_data(as_text=True)
    assert 'src="/static/js/admin.js"' in admin_html

    # Verify all static CSS and JS files load with 200 OK
    static_files = [
        "/static/css/variables.css",
        "/static/css/base.css",
        "/static/css/auth.css",
        "/static/css/dashboard.css",
        "/static/css/components.css",
        "/static/js/api.js",
        "/static/js/auth.js",
        "/static/js/charts.js",
        "/static/js/mock-data.js",
        "/static/js/student.js",
        "/static/js/faculty.js",
        "/static/js/admin.js"
    ]
    for asset in static_files:
        res = client.get(asset)
        assert res.status_code == 200, f"Static asset failed to load: {asset}"


def test_api_404_handler(client):
    res = client.get("/api/unknown_endpoint")
    assert res.status_code == 404
    data = res.get_json()
    assert data["success"] is False
    assert "Endpoint not found" in data["error"]


def test_demo_mode_disclaimers_removed_from_ui(client):
    """Confirms that Demo Mode banners and Simulated Analytics notices are removed from all rendered views."""
    views = [
        ("/", None),
        ("/login", None),
        ("/register", None),
        ("/student-dashboard", "student"),
        ("/faculty-dashboard", "faculty"),
        ("/admin-dashboard", "admin")
    ]
    removed_phrases = [
        "Simulated Academic Analytics:",
        "Student topic performance, weak-topic detection, and AI recommendations are loaded from client-side mock datasets. Live database sync will integrate in Phase 2.",
        "Simulated Faculty Roster:",
        "Simulated Admin Governance:",
        "Simulated Prototype Mode",
        "dashboard-demo-banner",
        "demo-banner-badge",
        "Active Model (Simulated)"
    ]
    for path, role in views:
        if role:
            set_session_role(client, role)
        html = client.get(path).get_data(as_text=True)
        for phrase in removed_phrases:
            assert phrase not in html, f"Found removed disclaimer '{phrase}' in view {path}"


def test_ai_study_assistant_responsive_layout_css(client):
    """Confirms that the AI Study Assistant and Student Dashboard CSS prevent horizontal overflow."""
    dashboard_css = client.get("/static/css/dashboard.css").get_data(as_text=True)
    components_css = client.get("/static/css/components.css").get_data(as_text=True)

    # Grid columns must use minmax(0, ...) and .dashboard-grid-column must have min-width: 0
    assert "minmax(0, 1.35fr) minmax(0, 1fr)" in dashboard_css
    assert ".dashboard-grid-column" in dashboard_css
    assert "overflow-x: hidden" in dashboard_css

    # AI Study Assistant container, message stream, chips, and input must constrain width and wrap content
    assert ".ai-assistant-card" in components_css
    assert "overflow-wrap: anywhere" in components_css
    assert ".ai-assistant-card pre" in components_css
    assert ".ai-assistant-card code" in components_css
    assert "flex-wrap: wrap" in components_css
    assert "@media (max-width: 768px)" in components_css


def test_study_assistant_chat_validation(client):
    """Validates empty messages and malformed requests on /api/study-assistant/chat."""
    set_session_role(client, "student")
    # Non-JSON request
    res_non_json = client.post("/api/study-assistant/chat", data="not json")
    assert res_non_json.status_code == 400
    assert res_non_json.get_json()["error_code"] == "INVALID_REQUEST"

    # Empty message
    res_empty = client.post("/api/study-assistant/chat", json={"message": "   "})
    assert res_empty.status_code == 400
    assert res_empty.get_json()["error_code"] == "EMPTY_MESSAGE"

    # Malformed history
    res_bad_history = client.post(
        "/api/study-assistant/chat",
        json={"message": "Explain recursion", "history": "not-a-list"}
    )
    assert res_bad_history.status_code == 400
    assert res_bad_history.get_json()["error_code"] == "INVALID_HISTORY"


def test_study_assistant_chat_missing_api_key(client, monkeypatch):
    """Returns 503 MISSING_API_KEY when GEMINI_API_KEY is unset or set to placeholder."""
    import services.study_assistant as sa

    set_session_role(client, "student")
    monkeypatch.setattr(sa, "_get_api_key", lambda: "")
    res = client.post(
        "/api/study-assistant/chat",
        json={"message": "Explain binary search trees in Python"}
    )
    assert res.status_code == 503
    data = res.get_json()
    assert data["success"] is False
    assert data["error_code"] == "MISSING_API_KEY"
    assert "GEMINI_API_KEY" in data["error"]


def test_study_assistant_chat_success_and_context(client, monkeypatch):
    """Verifies /api/study-assistant/chat invokes Gemini Interactions API and returns real model output."""
    import app as flask_app

    set_session_role(client, "student", user_id=1)
    captured_calls = []

    class DummyInteraction:
        id = "int_gemini_test_001"
        output_text = (
            "A **Binary Search Tree (BST)** is a hierarchical data structure where each node's "
            "left subtree contains smaller keys and right subtree contains larger keys.\n\n"
            "```python\nclass Node:\n    def __init__(self, key):\n        self.key = key\n```"
        )

    def fake_generate_reply(message, history=None, previous_interaction_id=None, student_context=None):
        captured_calls.append({
            "message": message,
            "history": history,
            "previous_interaction_id": previous_interaction_id,
            "student_context": student_context,
        })
        return {
            "reply": DummyInteraction.output_text,
            "model": "gemini-3.8-flash",
            "interaction_id": DummyInteraction.id,
            "grounded_in_student_data": bool(student_context),
        }

    monkeypatch.setattr(flask_app, "generate_study_assistant_reply", fake_generate_reply)

    res = client.post(
        "/api/study-assistant/chat",
        json={
            "message": "Explain binary search trees in Python",
            "history": [{"role": "user", "content": "Hi"}],
            "previous_interaction_id": "int_prev_000",
            "student_id": 1,
        }
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert "Binary Search Tree" in body["data"]["reply"]
    assert body["data"]["model"] == "gemini-3.8-flash"
    assert body["data"]["interaction_id"] == "int_gemini_test_001"
    assert body["data"]["grounded_in_student_data"] is True
    assert len(captured_calls) == 1
    assert captured_calls[0]["student_context"]["profile"]["name"] == "Aanya Patel"


def test_study_assistant_service_sdk_and_error_handling(monkeypatch):
    """Tests generate_study_assistant_reply with a mocked google-genai Client for success, quota, and network errors."""
    import services.study_assistant as sa
    import httpx

    monkeypatch.setattr(sa, "_get_api_key", lambda: "test_secret_gemini_key_12345")

    class FakeInteraction:
        id = "int_live_99"
        output_text = "Recursion is when a function calls itself with a smaller subproblem until reaching a base case."

    class FakeInteractionsResource:
        def __init__(self):
            self.last_kwargs = None

        def create(self, **kwargs):
            self.last_kwargs = kwargs
            return FakeInteraction()

    class FakeClient:
        def __init__(self):
            self.interactions = FakeInteractionsResource()

    fake_client = FakeClient()
    result = sa.generate_study_assistant_reply(
        message="What is recursion?",
        history=[{"role": "user", "content": "Hello"}],
        client_override=fake_client,
    )
    assert result["reply"].startswith("Recursion is when a function")
    assert result["interaction_id"] == "int_live_99"
    assert fake_client.interactions.last_kwargs["model"] == "gemini-3.5-flash-lite"
    assert "Recent conversation context:" in fake_client.interactions.last_kwargs["input"]

    # Quota error handling (and ensure API key is never leaked)
    class QuotaClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("429 RESOURCE_EXHAUSTED for key test_secret_gemini_key_12345")

    try:
        sa.generate_study_assistant_reply(message="Test quota", client_override=QuotaClient())
        assert False, "Expected StudyAssistantQuotaError"
    except sa.StudyAssistantQuotaError as qe:
        assert "test_secret_gemini_key_12345" not in str(qe)
        assert qe.status_code == 429
        assert qe.error_code == "QUOTA_EXCEEDED"

    # Timeout error handling (504 REQUEST_TIMEOUT)
    class TimeoutClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                raise httpx.ReadTimeout("Timed out")

    try:
        sa.generate_study_assistant_reply(message="Test timeout", client_override=TimeoutClient())
        assert False, "Expected StudyAssistantTimeoutError"
    except sa.StudyAssistantTimeoutError as te:
        assert te.status_code == 504
        assert te.error_code == "REQUEST_TIMEOUT"

    # Network connection error handling (503 NETWORK_ERROR)
    class NetworkClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                raise httpx.ConnectError("Connection refused")

    try:
        sa.generate_study_assistant_reply(message="Test network", client_override=NetworkClient())
        assert False, "Expected StudyAssistantNetworkError"
    except sa.StudyAssistantNetworkError as ne:
        assert ne.status_code == 503
        assert ne.error_code == "NETWORK_ERROR"

    # Authentication error handling (401 INVALID_API_KEY)
    class AuthClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("401 UNAUTHENTICATED: API_KEY_INVALID for test_secret_gemini_key_12345")

    try:
        sa.generate_study_assistant_reply(message="Test auth", client_override=AuthClient())
        assert False, "Expected StudyAssistantAuthError"
    except sa.StudyAssistantAuthError as ae:
        assert "test_secret_gemini_key_12345" not in str(ae)
        assert ae.status_code == 401
        assert ae.error_code == "INVALID_API_KEY"

    # Invalid model error handling (400 INVALID_MODEL)
    class ModelClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("404 Model not found")

    try:
        sa.generate_study_assistant_reply(message="Test model", client_override=ModelClient())
        assert False, "Expected StudyAssistantModelError"
    except sa.StudyAssistantModelError as me:
        assert me.status_code == 400
        assert me.error_code == "INVALID_MODEL"


def test_frontend_student_js_uses_live_gemini_endpoint(client):
    """Confirms static/js/student.js and static/js/api.js call /study-assistant/chat and do not use simulated AI responses."""
    student_js = client.get("/static/js/student.js").get_data(as_text=True)
    api_js = client.get("/static/js/api.js").get_data(as_text=True)

    assert "sendStudyAssistantMessage" in api_js
    assert "/study-assistant/chat" in api_js
    assert "sendStudyAssistantMessage" in student_js
    assert "function generateAIResponse" not in student_js


# ==========================================
# 9. Priorities 1–5 End-to-End Integration Tests
# ==========================================

def test_priority_1_registration_redirect_in_auth_js(client):
    """Priority 1: Confirms auth.js redirects to /login?registered=1 with 'Registration successful. Please log in.' on confirmed registration."""
    auth_js = client.get("/static/js/auth.js").get_data(as_text=True)
    assert "Registration successful. Please log in." in auth_js
    assert "/login?registered=1" in auth_js
    assert "edunexus_registration_success" in auth_js


def test_priority_2_newly_registered_student_dashboard_and_admin_overview(client):
    """Priority 2: Newly registered student sees real profile and 0 submissions (no fabricated data); admin sees real users."""
    reg_res = client.post("/api/auth/register", json={
        "fullName": "Neha Verma",
        "email": "neha.verma@edunexus.edu",
        "password": "Password123!",
        "role": "student",
        "department": "Data Structures"
    })
    assert reg_res.status_code == 201
    new_user = reg_res.get_json()["data"]["user"]
    student_id = new_user["id"]

    # Log in as the newly registered student and fetch their dashboard
    login_res = client.post("/api/auth/login", json={
        "email": "neha.verma@edunexus.edu",
        "password": "Password123!"
    })
    assert login_res.status_code == 200

    dash_res = client.get(f"/api/student/{student_id}/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.get_json()["data"]
    assert dash_data["profile"]["name"] == "Neha Verma"
    assert dash_data["profile"]["email"] == "neha.verma@edunexus.edu"
    assert dash_data["metrics"]["total_submissions"] == 0
    assert dash_data["metrics"]["overall_score"] == 0.0
    assert dash_data["weak_topics"] == []
    assert dash_data["recommendations"] == []

    # Student is forbidden from accessing Admin Overview (403)
    assert client.get("/api/admin/overview").status_code == 403

    # Log in as Admin and verify Admin Overview includes Neha Verma and supports status updates
    set_session_role(client, "admin")
    admin_res = client.get("/api/admin/overview")
    assert admin_res.status_code == 200
    admin_data = admin_res.get_json()["data"]
    assert admin_data["metrics"]["students_count"] >= 1
    emails = [u["email"] for u in admin_data["users"]]
    assert "neha.verma@edunexus.edu" in emails

    status_res = client.post("/api/admin/users/status", json={
        "role": "student",
        "record_id": student_id,
        "status": "Suspended"
    })
    assert status_res.status_code == 200
    assert status_res.get_json()["data"]["status"] == "Suspended"


def test_priority_3_faculty_student_interventions_and_targeted_practice(client):
    """Priority 3: Student 1-to-1 help requests, faculty responses, and targeted practice assignment."""
    # 1. Student requests 1-to-1 office hours
    set_session_role(client, "student", user_id=1)
    req_res = client.post("/api/interventions", json={
        "student_id": 1,
        "student_name": "Aanya Patel",
        "course_code": "CS-301",
        "topic": "Recursion",
        "intervention_type": "office_hours",
        "initiated_by": "student",
        "title": "1-to-1 Office Hours Request: Recursion",
        "details": "Need help tracing recursion tree depth."
    })
    assert req_res.status_code == 201
    intervention = req_res.get_json()["data"]
    intervention_id = intervention["id"]
    assert intervention["status"] == "open"

    # 2. Student cannot respond as faculty even if they pass role='faculty' in payload (403)
    forbidden_res = client.post(f"/api/interventions/{intervention_id}/respond", json={
        "role": "faculty",
        "status": "resolved",
        "faculty_response": "Self-approving"
    })
    assert forbidden_res.status_code == 403

    # 3. Faculty responds to the student's help request
    set_session_role(client, "faculty")
    resp_res = client.post(f"/api/interventions/{intervention_id}/respond", json={
        "role": "faculty",
        "status": "scheduled",
        "faculty_response": "Office hours scheduled for Thursday at 3 PM.",
        "faculty_name": "Dr. Sarah Mitchell"
    })
    assert resp_res.status_code == 200
    updated_int = resp_res.get_json()["data"]
    assert updated_int["status"] == "scheduled"
    assert "Thursday at 3 PM" in updated_int["faculty_response"]

    # 4. Faculty assigns targeted remedial quiz to Student #1
    act_res = client.post("/api/activities", json={
        "role": "faculty",
        "title": "Recursion Remedial Practice Set",
        "topic": "Recursion",
        "activity_type": "quiz",
        "max_score": 100,
        "assigned_student_id": 1,
        "instructions": "Complete base-case and recurrence relation problems."
    })
    assert act_res.status_code == 201
    act_data = act_res.get_json()["data"]
    assert act_data["assigned_student_id"] == 1


def test_priority_4_unified_course_hub_and_evaluation_queue(client):
    """Priority 4: Course Hub announcements/materials and Submissions & Evaluation Queue."""
    # Student role is blocked from publishing announcements or materials even if spoofing role in body
    set_session_role(client, "student", user_id=1)
    assert client.post("/api/announcements", json={
        "role": "faculty",
        "title": "Unauthorized",
        "message": "Should fail"
    }).status_code == 403

    assert client.post("/api/course-materials", json={
        "role": "faculty",
        "title": "Unauthorized",
        "content_or_url": "Should fail"
    }).status_code == 403

    # Faculty publishes announcement and material
    set_session_role(client, "faculty")
    ann_res = client.post("/api/announcements", json={
        "role": "faculty",
        "course_code": "CS-301",
        "title": "Midterm Exam Guidelines",
        "message": "Review Arrays, Stacks, and Recursion modules.",
        "priority": "important",
        "published_by": "Dr. Sarah Mitchell"
    })
    assert ann_res.status_code == 201

    mat_res = client.post("/api/course-materials", json={
        "role": "faculty",
        "course_code": "CS-301",
        "title": "Recursion & Call Stack Notes",
        "topic": "Recursion",
        "resource_type": "Lecture Notes",
        "content_or_url": "Comprehensive guide to base cases and stack frames.",
        "uploaded_by": "Dr. Sarah Mitchell"
    })
    assert mat_res.status_code == 201

    hub_res = client.get("/api/course-hub?course_code=CS-301")
    assert hub_res.status_code == 200
    hub_data = hub_res.get_json()["data"]
    assert any(a["title"] == "Midterm Exam Guidelines" for a in hub_data["announcements"])
    assert any(m["title"] == "Recursion & Call Stack Notes" for m in hub_data["materials"])

    # Student submits assignment response for evaluation
    set_session_role(client, "student", user_id=1)
    sub_res = client.post("/api/submissions", json={
        "student_id": 1,
        "activity_id": 1,
        "response_text": "Implemented O(n) two-pointer array traversal.",
        "status": "pending_review"
    })
    assert sub_res.status_code == 201
    submission_id = sub_res.get_json()["data"]["id"]

    # Student cannot grade their own submission even if spoofing role='faculty' (403)
    assert client.post(f"/api/submissions/{submission_id}/evaluate", json={
        "role": "faculty",
        "score": 100
    }).status_code == 403

    # Faculty evaluates submission with marks and written feedback
    set_session_role(client, "faculty")
    eval_res = client.post(f"/api/submissions/{submission_id}/evaluate", json={
        "role": "faculty",
        "score": 92,
        "feedback": "Excellent time complexity analysis and clean edge-case handling.",
        "evaluated_by": "Dr. Sarah Mitchell"
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.get_json()["data"]
    assert eval_data["score"] == 92.0
    assert eval_data["status"] == "evaluated"
    assert "Excellent time complexity" in eval_data["feedback"]


def test_priority_5_faculty_overview_explainable_insights(client):
    """Priority 5: Faculty overview includes explainable insights grounded in real submission evidence."""
    set_session_role(client, "faculty")
    res = client.get("/api/faculty/overview")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "explainable_insights" in data
    assert "insights_meta" in data
    assert data["insights_meta"]["has_sufficient_data"] is True
    assert len(data["explainable_insights"]) >= 1
    first_insight = data["explainable_insights"][0]
    assert "topic" in first_insight
    assert "evidence" in first_insight and isinstance(first_insight["evidence"], list)
    assert "recommended_action" in first_insight


# ==========================================
# 10. Full Role-Based Access Control (RBAC) Matrix
# ==========================================

def test_rbac_all_roles_and_unauthenticated_protection(client):
    """
    Verifies all 8 security scenarios:
    1. Unauthenticated access to dashboards redirects to /login; APIs return 401.
    2. Student registration -> /login -> Student login -> /student-dashboard only.
    3. Student blocked from Faculty and Admin dashboards and APIs (403).
    4. Faculty login (FACULTY_EMAIL / FACULTY_PASSWORD) -> /faculty-dashboard only; blocked from Student & Admin (403).
    5. Admin login (ADMIN_EMAIL / ADMIN_PASSWORD) -> /admin-dashboard only; blocked from Student & Faculty (403).
    6. Invalid credentials rejected with 401.
    7. Logout invalidates session and blocks subsequent access.
    """
    # 1. Unauthenticated requests
    assert client.get("/student-dashboard").status_code == 302
    assert client.get("/faculty-dashboard").status_code == 302
    assert client.get("/admin-dashboard").status_code == 302
    assert client.get("/api/student/1/dashboard").status_code == 401
    assert client.get("/api/faculty/overview").status_code == 401
    assert client.get("/api/admin/overview").status_code == 401

    # 2 & 3. Student Registration, Login, and RBAC
    reg_res = client.post("/api/auth/register", json={
        "fullName": "RBAC Student",
        "email": "rbac.student@edunexus.edu",
        "password": "StudentPass123!",
        "role": "student"
    })
    assert reg_res.status_code == 201
    assert reg_res.get_json()["data"]["redirectUrl"] == "/login"

    std_login = client.post("/api/auth/login", json={
        "email": "rbac.student@edunexus.edu",
        "password": "StudentPass123!"
    })
    assert std_login.status_code == 200
    assert std_login.get_json()["data"]["redirectUrl"] == "/student-dashboard"
    assert client.get("/student-dashboard").status_code == 200
    assert client.get("/faculty-dashboard").status_code == 403
    assert client.get("/admin-dashboard").status_code == 403
    assert client.get("/api/faculty/overview").status_code == 403
    assert client.get("/api/admin/overview").status_code == 403
    assert client.post("/api/admin/users/status", json={"role": "student", "record_id": 1, "status": "Active"}).status_code == 403

    # 4. Faculty Login (from environment variables) and RBAC
    faculty_email = os.getenv("FACULTY_EMAIL", "faculty@edunexus.com")
    faculty_password = os.getenv("FACULTY_PASSWORD")
    fac_login = client.post("/api/auth/login", json={
        "email": faculty_email,
        "password": faculty_password
    })
    assert fac_login.status_code == 200
    assert fac_login.get_json()["data"]["user"]["role"] == "faculty"
    assert fac_login.get_json()["data"]["redirectUrl"] == "/faculty-dashboard"
    assert client.get("/faculty-dashboard").status_code == 200
    assert client.get("/api/faculty/overview").status_code == 200
    assert client.get("/student-dashboard").status_code == 403
    assert client.get("/admin-dashboard").status_code == 403
    assert client.get("/api/admin/overview").status_code == 403

    # 5. Admin Login (from environment variables) and RBAC
    admin_email = os.getenv("ADMIN_EMAIL", "admin@edunexus.com")
    admin_password = os.getenv("ADMIN_PASSWORD")
    adm_login = client.post("/api/auth/login", json={
        "email": admin_email,
        "password": admin_password
    })
    assert adm_login.status_code == 200
    assert adm_login.get_json()["data"]["user"]["role"] == "admin"
    assert adm_login.get_json()["data"]["redirectUrl"] == "/admin-dashboard"
    assert client.get("/admin-dashboard").status_code == 200
    assert client.get("/api/admin/overview").status_code == 200
    assert client.get("/student-dashboard").status_code == 403
    assert client.get("/faculty-dashboard").status_code == 403
    assert client.get("/api/faculty/overview").status_code == 403

    # 6. Invalid credentials rejected (401)
    assert client.post("/api/auth/login", json={"email": admin_email, "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": faculty_email, "password": "wrong"}).status_code == 401

    # 7. Logout invalidates session
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/admin-dashboard").status_code == 302
    assert client.get("/api/admin/overview").status_code == 401




