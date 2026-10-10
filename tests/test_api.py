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
    assert "diagnostics" in data["database"]
    assert "failure_category" in data["database"]["diagnostics"]
    assert "message" in data["database"]["diagnostics"]


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


def test_auth_register_faculty(client):
    payload = {
        "fullName": "Dr. Vikram Sarabhai",
        "email": "vikram.faculty@example.com",
        "password": "Password123!",
        "role": "faculty"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
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


def test_navigation_links_and_static_assets(client):
    # Verify Home page links
    home_html = client.get("/").get_data(as_text=True)
    assert 'href="/login"' in home_html
    assert 'href="/register"' in home_html
    assert 'href="/student-dashboard"' in home_html
    assert 'href="/faculty-dashboard"' in home_html
    assert 'href="/admin-dashboard"' in home_html
    assert "templates/" not in home_html

    # Verify Login page links & static URLs
    login_html = client.get("/login").get_data(as_text=True)
    assert 'href="/register"' in login_html
    assert 'href="/static/css/auth.css"' in login_html
    assert 'src="/static/js/auth.js"' in login_html
    assert "register.html" not in login_html
    assert "../static" not in login_html

    # Verify Register page links & static URLs
    reg_html = client.get("/register").get_data(as_text=True)
    assert 'href="/login"' in reg_html
    assert 'href="/static/css/auth.css"' in reg_html
    assert 'src="/static/js/auth.js"' in reg_html

    # Verify Dashboard cross-links
    student_html = client.get("/student-dashboard").get_data(as_text=True)
    assert 'href="/faculty-dashboard"' in student_html
    assert 'href="/admin-dashboard"' in student_html
    assert 'src="/static/js/student.js"' in student_html

    faculty_html = client.get("/faculty-dashboard").get_data(as_text=True)
    assert 'href="/student-dashboard"' in faculty_html
    assert 'href="/admin-dashboard"' in faculty_html
    assert 'src="/static/js/faculty.js"' in faculty_html

    admin_html = client.get("/admin-dashboard").get_data(as_text=True)
    assert 'href="/student-dashboard"' in admin_html
    assert 'href="/faculty-dashboard"' in admin_html
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
        "/",
        "/login",
        "/register",
        "/student-dashboard",
        "/faculty-dashboard",
        "/admin-dashboard"
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
    for path in views:
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


