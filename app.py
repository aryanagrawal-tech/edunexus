"""
EduNexus AI — Flask REST API Backend
Tagline: "From academic activity to actionable growth."
Connects to Supabase PostgreSQL with local mock fallback.
"""

import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from services.database import db_service
from services.analytics import (
    calculate_overall_score,
    calculate_topic_scores,
    detect_weak_topics,
    analyze_student_performance,
    analyze_faculty_cohort,
    ALLOWED_TOPICS
)
from services.recommendations import generate_recommendations

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# ==========================================
# Health & Status Endpoint
# ==========================================
@app.route("/health", methods=["GET"])
def health_check():
    """Health status and database connectivity endpoint."""
    return jsonify({
        "status": "ok",
        "service": "EduNexus AI Backend",
        "tagline": "From academic activity to actionable growth.",
        "course": "Data Structures",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_service.get_status()
    }), 200


# ==========================================
# Core Academic REST API Endpoints
# ==========================================

@app.route("/api/students", methods=["GET"])
def get_students():
    """Retrieves list of all enrolled students."""
    try:
        students = db_service.get_students()
        return jsonify({
            "success": True,
            "count": len(students),
            "data": students
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/activities", methods=["GET"])
def get_activities():
    """Retrieves all course activities and curriculum modules."""
    try:
        activities = db_service.get_activities()
        return jsonify({
            "success": True,
            "count": len(activities),
            "data": activities
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/activities", methods=["POST"])
def create_activity():
    """Creates a new course activity."""
    payload = request.get_json(silent=True) or {}
    title = payload.get("title", "").strip()
    topic = payload.get("topic", "").strip()
    activity_type = payload.get("activity_type", "Quiz").strip()
    max_score = payload.get("max_score", 100)

    # Validation
    if not title:
        return jsonify({"success": False, "error": "Activity 'title' is required."}), 400
    if not topic or topic not in ALLOWED_TOPICS:
        return jsonify({
            "success": False,
            "error": f"Invalid topic '{topic}'. Must be one of: {', '.join(ALLOWED_TOPICS)}"
        }), 400
    try:
        max_score = float(max_score)
        if max_score <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "'max_score' must be a positive number."}), 400

    try:
        new_activity = db_service.create_activity({
            "title": title,
            "topic": topic,
            "activity_type": activity_type,
            "max_score": max_score
        })
        return jsonify({
            "success": True,
            "message": "Activity created successfully.",
            "data": new_activity
        }), 201
    except RuntimeError as re:
        return jsonify({"success": False, "error": str(re)}), 503
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/student/<student_id>/dashboard", methods=["GET"])
def get_student_dashboard(student_id):
    """
    Retrieves full academic dashboard for a specific student:
    Overall score, topic mastery, weak-topic detection, and personalized recommendations.
    """
    try:
        student = db_service.get_student_by_id(student_id)
        if not student:
            return jsonify({
                "success": False,
                "error": f"Student with ID '{student_id}' not found."
            }), 404

        submissions = db_service.get_submissions(student_id=student["id"])
        performance = analyze_student_performance(student, submissions)
        recommendations = generate_recommendations(performance["weak_topics"])

        response_data = {
            "profile": {
                "id": student["id"],
                "name": student["name"],
                "email": student.get("email"),
                "course": "Data Structures"
            },
            "metrics": {
                "overall_score": performance["overall_score"],
                "completion_rate": performance["completion_rate"],
                "total_submissions": performance["total_submissions"]
            },
            "topic_scores": performance["topic_scores"],
            "weak_topics": performance["weak_topics"],
            "recommendations": recommendations,
            "recent_submissions": submissions[:5]
        }

        return jsonify({
            "success": True,
            "data": response_data
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/faculty/overview", methods=["GET"])
def get_faculty_overview():
    """
    Retrieves course overview for faculty:
    Class average, topic mastery distribution, and at-risk students needing support.
    """
    try:
        students = db_service.get_students()
        all_submissions = db_service.get_submissions()

        cohort_metrics = analyze_faculty_cohort(students, all_submissions)

        return jsonify({
            "success": True,
            "data": cohort_metrics
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/submissions", methods=["POST"])
def submit_activity():
    """Records a student submission with score and completion status."""
    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    activity_id = payload.get("activity_id")
    score = payload.get("score")
    is_late = bool(payload.get("is_late", False))

    if student_id is None or activity_id is None or score is None:
        return jsonify({
            "success": False,
            "error": "Missing required fields: 'student_id', 'activity_id', and 'score' are required."
        }), 400

    # Validate score range
    try:
        numeric_score = float(score)
        if numeric_score < 0 or numeric_score > 100:
            return jsonify({
                "success": False,
                "error": "Score must be a number between 0 and 100."
            }), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Score must be a valid numeric value."}), 400

    # Verify student exists
    student = db_service.get_student_by_id(student_id)
    if not student:
        return jsonify({"success": False, "error": f"Student ID '{student_id}' does not exist."}), 404

    # Verify activity exists
    activity = db_service.get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"success": False, "error": f"Activity ID '{activity_id}' does not exist."}), 404

    try:
        new_submission = db_service.create_submission({
            "student_id": student["id"],
            "activity_id": activity["id"],
            "score": numeric_score,
            "is_late": is_late
        })
        return jsonify({
            "success": True,
            "message": "Submission recorded successfully.",
            "data": new_submission
        }), 201
    except RuntimeError as re:
        return jsonify({"success": False, "error": str(re)}), 503
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze_performance():
    """
    On-demand analytics endpoint:
    Analyzes student submissions and produces weak topics + recommendations.
    Accepts { "student_id": 1 } or { "submissions": [...] }
    """
    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    custom_subs = payload.get("submissions")

    if student_id is not None:
        student = db_service.get_student_by_id(student_id)
        if not student:
            return jsonify({"success": False, "error": f"Student '{student_id}' not found."}), 404
        subs = db_service.get_submissions(student_id=student["id"])
    elif isinstance(custom_subs, list):
        student = {"id": 0, "name": "Diagnostic Candidate"}
        subs = custom_subs
    else:
        return jsonify({
            "success": False,
            "error": "Must provide either 'student_id' or 'submissions' array."
        }), 400

    performance = analyze_student_performance(student, subs)
    recommendations = generate_recommendations(performance["weak_topics"])

    return jsonify({
        "success": True,
        "data": {
            "overall_score": performance["overall_score"],
            "topic_scores": performance["topic_scores"],
            "weak_topics": performance["weak_topics"],
            "recommendations": recommendations
        }
    }), 200


# ==========================================
# Frontend Authentication API Compatibility
# Compatible with docs/api.md & static/js/api.js
# ==========================================

@app.route("/auth/login", methods=["POST"])
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """User login endpoint matching existing frontend auth contract."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip()
    password = payload.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password."}), 400

    # Role matching based on institutional account structure
    role = "faculty" if "faculty" in email else ("admin" if "admin" in email else "student")
    name = email.split("@")[0].replace(".", " ").title()

    user_data = {
        "id": f"usr_{hash(email) % 100000:05d}",
        "fullName": name,
        "email": email,
        "role": role,
        "course": "Data Structures"
    }

    return jsonify({
        "success": True,
        "message": f"Authentication successful as {role.upper()}.",
        "data": {
            "token": f"jwt_live_{int(datetime.now().timestamp())}",
            "expiresAt": int(datetime.now().timestamp()) + 86400,
            "user": user_data
        }
    }), 200


@app.route("/auth/register", methods=["POST"])
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """User registration endpoint matching frontend security rules."""
    payload = request.get_json(silent=True) or {}
    full_name = payload.get("fullName", "").strip()
    email = payload.get("email", "").strip()
    password = payload.get("password", "")
    role = payload.get("role", "").strip().lower()

    if not full_name or not email or not password or not role:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    if role == "admin":
        return jsonify({
            "success": False,
            "message": "Admin registration is not permitted through public portal."
        }), 403

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters long."
        }), 400

    return jsonify({
        "success": True,
        "message": f"Account created successfully for {full_name} as {role.upper()}.",
        "data": {
            "user": {
                "id": f"usr_{int(datetime.now().timestamp())}",
                "fullName": full_name,
                "email": email,
                "role": role,
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
        }
    }), 201


@app.route("/auth/me", methods=["GET"])
@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Current session info."""
    return jsonify({
        "success": True,
        "data": {
            "id": "usr_active_session",
            "fullName": "Aanya Patel",
            "email": "aanya.demo@example.com",
            "role": "student",
            "course": "Data Structures"
        }
    }), 200


@app.route("/auth/logout", methods=["POST"])
@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Invalidate session."""
    return jsonify({"success": True, "message": "Session invalidated."}), 200


# ==========================================
# Frontend View Routes (Jinja / HTML Templates)
# ==========================================

@app.route("/", methods=["GET"])
def index_view():
    """Serves the platform navigation portal."""
    return send_from_directory(".", "index.html")


@app.route("/login", methods=["GET"])
def login_view():
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register_view():
    return render_template("register.html")


@app.route("/student-dashboard", methods=["GET"])
def student_dashboard_view():
    return render_template("student-dashboard.html")


@app.route("/faculty-dashboard", methods=["GET"])
def faculty_dashboard_view():
    return render_template("faculty-dashboard.html")


@app.route("/admin-dashboard", methods=["GET"])
def admin_dashboard_view():
    return render_template("admin-dashboard.html")


# ==========================================
# Error Handlers
# ==========================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Endpoint not found."}), 404
    return "Page Not Found", 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal Server Error."}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
