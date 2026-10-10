"""
EduNexus AI — Flask REST API Backend
Tagline: "From academic activity to actionable growth."
Connects to Supabase PostgreSQL with local mock fallback.
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

from services.database import db_service, DuplicateAccountError
from services.analytics import (
    calculate_overall_score,
    calculate_topic_scores,
    detect_weak_topics,
    analyze_student_performance,
    analyze_faculty_cohort,
    generate_explainable_faculty_insights,
    ALLOWED_TOPICS
)
from services.recommendations import generate_recommendations
from services.study_assistant import (
    generate_study_assistant_reply,
    StudyAssistantError,
    is_gemini_configured,
    DEFAULT_GEMINI_MODEL,
)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = (
    os.getenv("FLASK_SECRET_KEY")
    or os.getenv("SECRET_KEY")
    or "edunexus-ai-secure-session-key"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
CORS(app, supports_credentials=True)

DASHBOARD_BY_ROLE = {
    "student": "/student-dashboard",
    "faculty": "/faculty-dashboard",
    "admin": "/admin-dashboard",
}


def get_session_user():
    """Returns the currently authenticated user dict from the server-side Flask session."""
    user = session.get("user")
    if isinstance(user, dict) and user.get("role") and user.get("email"):
        return user
    return None


def require_api_auth(allowed_roles=None):
    """
    Verifies that the request has a valid server-side session and an authorized role.
    Never trusts client-supplied role parameters over the server-side session.
    """
    user = get_session_user()
    if not user:
        return None, (
            jsonify({
                "success": False,
                "error": "Authentication required. Please log in.",
                "message": "Authentication required. Please log in."
            }),
            401,
        )

    actual_role = str(user.get("role", "")).strip().lower()
    if allowed_roles is not None:
        normalized_allowed = {r.strip().lower() for r in allowed_roles}
        if actual_role not in normalized_allowed:
            return None, (
                jsonify({
                    "success": False,
                    "error": f"Forbidden: Role '{actual_role}' is not authorized for this resource.",
                    "message": f"Forbidden: Role '{actual_role}' is not authorized for this resource."
                }),
                403,
            )

    return user, None


@app.after_request
def apply_security_headers(response):
    """Prevents browser caching of protected dashboard pages and API responses after logout."""
    path = request.path or ""
    if (
        path.startswith("/student-dashboard")
        or path.startswith("/faculty-dashboard")
        or path.startswith("/admin-dashboard")
        or path.startswith("/api/")
        or path.startswith("/auth/")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


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
    """Retrieves list of all enrolled students (Faculty & Admin only)."""
    _, err_resp = require_api_auth(["faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        students = db_service.get_students()
        return jsonify({
            "success": True,
            "count": len(students),
            "data": students
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/faculty", methods=["GET"])
def get_faculty():
    """Retrieves list of all registered faculty members (Faculty & Admin only)."""
    _, err_resp = require_api_auth(["faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        faculty = db_service.get_faculty()
        return jsonify({
            "success": True,
            "count": len(faculty),
            "data": faculty
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/activities", methods=["GET"])
def get_activities():
    """Retrieves course activities and curriculum modules (optionally filtered for a student)."""
    _, err_resp = require_api_auth(["student", "faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        student_id = request.args.get("student_id")
        activities = db_service.get_activities(student_id=student_id)
        return jsonify({
            "success": True,
            "count": len(activities),
            "data": activities
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/activities", methods=["POST"])
def create_activity():
    """Creates a new course activity or targeted student exercise (Faculty & Admin only)."""
    user, err_resp = require_api_auth(["faculty", "admin"])
    if err_resp:
        return err_resp

    payload = request.get_json(silent=True) or {}

    title = payload.get("title", "").strip()
    topic = payload.get("topic", "").strip()
    activity_type = payload.get("activity_type", "Quiz").strip()
    max_score = payload.get("max_score", 100)
    instructions = (payload.get("instructions") or "").strip()
    due_date = (payload.get("due_date") or "").strip()
    assigned_student_id = payload.get("assigned_student_id")
    course_code = (payload.get("course_code") or "CS-301").strip()
    created_by_faculty = (payload.get("created_by_faculty") or user.get("name") or "Course Faculty").strip()

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

    if assigned_student_id is not None and str(assigned_student_id).strip() != "":
        target_student = db_service.get_student_by_id(assigned_student_id)
        if not target_student:
            return jsonify({"success": False, "error": f"Target student ID '{assigned_student_id}' not found."}), 404
        assigned_student_id = target_student["id"]
    else:
        assigned_student_id = None

    try:
        new_activity = db_service.create_activity({
            "title": title,
            "topic": topic,
            "activity_type": activity_type,
            "max_score": max_score,
            "instructions": instructions,
            "due_date": due_date,
            "assigned_student_id": assigned_student_id,
            "course_code": course_code,
            "created_by_faculty": created_by_faculty
        })

        # If assigned to a specific student, also record a collaboration notification
        if assigned_student_id is not None:
            try:
                db_service.create_intervention({
                    "student_id": assigned_student_id,
                    "faculty_name": created_by_faculty,
                    "course_code": course_code,
                    "topic": topic,
                    "intervention_type": "targeted_practice",
                    "initiated_by": "faculty",
                    "title": f"Assigned {activity_type}: {title}",
                    "message": instructions or f"Please complete '{title}' ({topic}) to strengthen your mastery.",
                    "status": "Assigned"
                })
            except Exception:
                pass

        return jsonify({
            "success": True,
            "message": "Activity created successfully.",
            "data": new_activity
        }), 201
    except RuntimeError as re_err:
        return jsonify({"success": False, "error": str(re_err)}), 503
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/student/<student_id>/dashboard", methods=["GET"])
def get_student_dashboard(student_id):
    """
    Retrieves full academic dashboard for a specific student:
    Real profile, overall score, topic mastery, weak-topic detection,
    personalized recommendations, assigned activities, submissions, and faculty collaboration items.
    """
    _, err_resp = require_api_auth(["student"])
    if err_resp:
        return err_resp
    try:
        student = db_service.get_student_by_id(student_id)
        if not student:
            email_param = (request.args.get("email") or "").strip().lower()
            if email_param:
                user_lookup = db_service.get_user_by_email(email_param)
                if user_lookup and user_lookup.get("role") == "student":
                    student = db_service.get_student_by_id(user_lookup.get("id"))

        if not student:
            return jsonify({
                "success": False,
                "error": f"Student with ID '{student_id}' not found."
            }), 404

        submissions = db_service.get_submissions(student_id=student["id"])
        assigned_activities = db_service.get_activities(student_id=student["id"])
        performance = analyze_student_performance(
            student,
            submissions,
            total_assigned_activities=len(assigned_activities) or 6
        )
        recommendations = generate_recommendations(performance["weak_topics"]) if submissions else []
        interventions = db_service.get_interventions(student_id=student["id"])
        courses = db_service.get_courses()
        materials = db_service.get_course_materials()
        announcements = db_service.get_announcements()

        response_data = {
            "profile": {
                "id": student["id"],
                "name": student["name"],
                "email": student.get("email"),
                "course": student.get("course") or "Data Structures",
                "status": student.get("status") or "Active",
                "created_at": student.get("created_at")
            },
            "metrics": {
                "overall_score": performance["overall_score"],
                "completion_rate": performance["completion_rate"],
                "total_submissions": performance["total_submissions"],
                "total_assigned_activities": len(assigned_activities),
                "has_assessment_data": len(submissions) > 0
            },
            "topic_scores": performance["topic_scores"] if submissions else [],
            "weak_topics": performance["weak_topics"],
            "recommendations": recommendations,
            "recent_submissions": submissions,
            "assigned_activities": assigned_activities,
            "interventions": interventions,
            "course_hub": {
                "courses": courses,
                "materials": materials,
                "announcements": announcements
            }
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
    Retrieves real course overview for faculty:
    Class average, topic mastery distribution, at-risk students needing support,
    explainable AI insights, evaluation queue, interventions, and course hub data.
    """
    _, err_resp = require_api_auth(["faculty"])
    if err_resp:
        return err_resp
    try:
        students = db_service.get_students()
        all_submissions = db_service.get_submissions()
        activities = db_service.get_activities()
        courses = db_service.get_courses()
        materials = db_service.get_course_materials()
        announcements = db_service.get_announcements()
        interventions = db_service.get_interventions()
        faculty_list = db_service.get_faculty()

        cohort_metrics = analyze_faculty_cohort(students, all_submissions, activities=activities)
        cohort_metrics["courses"] = courses
        cohort_metrics["activities"] = activities
        cohort_metrics["submissions_queue"] = all_submissions
        cohort_metrics["interventions"] = interventions
        cohort_metrics["students_roster"] = [
            {"id": s["id"], "name": s["name"], "email": s.get("email")}
            for s in students
        ]
        cohort_metrics["faculty_roster"] = faculty_list
        cohort_metrics["course_hub"] = {
            "courses": courses,
            "materials": materials,
            "announcements": announcements
        }

        return jsonify({
            "success": True,
            "data": cohort_metrics
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/submissions", methods=["GET"])
def list_submissions():
    """Retrieves submissions, optionally filtered by student_id."""
    _, err_resp = require_api_auth(["student", "faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        student_id = request.args.get("student_id")
        subs = db_service.get_submissions(student_id=student_id)
        return jsonify({
            "success": True,
            "count": len(subs),
            "data": subs
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/submissions", methods=["POST"])
def submit_activity():
    """Records a student submission with score or assignment response text."""
    _, err_resp = require_api_auth(["student"])
    if err_resp:
        return err_resp
    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    activity_id = payload.get("activity_id")
    score = payload.get("score")
    response_text = (payload.get("response_text") or "").strip()
    is_late = bool(payload.get("is_late", False))

    if student_id is None or activity_id is None or (score is None and not response_text):
        return jsonify({
            "success": False,
            "error": "Missing required fields: 'student_id', 'activity_id', and 'score' are required."
        }), 400

    if score is not None and str(score).strip() != "":
        try:
            numeric_score = float(score)
            if numeric_score < 0 or numeric_score > 100:
                return jsonify({
                    "success": False,
                    "error": "Score must be a number between 0 and 100."
                }), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Score must be a valid numeric value."}), 400
        default_status = "late" if is_late else (payload.get("status") or "submitted")
    else:
        numeric_score = 0.0
        default_status = "pending_review"

    student = db_service.get_student_by_id(student_id)
    if not student:
        return jsonify({"success": False, "error": f"Student ID '{student_id}' does not exist."}), 404

    activity = db_service.get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"success": False, "error": f"Activity ID '{activity_id}' does not exist."}), 404

    try:
        new_submission = db_service.create_submission({
            "student_id": student["id"],
            "activity_id": activity["id"],
            "score": numeric_score,
            "is_late": is_late,
            "status": default_status,
            "response_text": response_text
        })
        return jsonify({
            "success": True,
            "message": "Submission recorded successfully.",
            "data": new_submission
        }), 201
    except RuntimeError as re_err:
        return jsonify({"success": False, "error": str(re_err)}), 503
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/submissions/<submission_id>/evaluate", methods=["POST", "PUT", "PATCH"])
def evaluate_submission_route(submission_id):
    """
    Allows faculty to evaluate a student submission with marks and feedback.
    Enforces role-based authorization: students cannot modify faculty evaluation records.
    """
    user, err_resp = require_api_auth(["faculty"])
    if err_resp:
        return err_resp

    payload = request.get_json(silent=True) or {}
    score = payload.get("score")
    feedback = (payload.get("feedback") or "").strip()
    evaluated_by = (payload.get("evaluated_by") or user.get("name") or "Course Faculty").strip()

    if score is None:
        return jsonify({"success": False, "error": "'score' is required to evaluate a submission."}), 400

    try:
        numeric_score = float(score)
        if numeric_score < 0 or numeric_score > 100:
            return jsonify({"success": False, "error": "Score must be between 0 and 100."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Score must be a valid number."}), 400

    try:
        updated = db_service.evaluate_submission(
            submission_id=submission_id,
            score=numeric_score,
            feedback=feedback,
            evaluated_by=evaluated_by
        )
        if not updated:
            return jsonify({"success": False, "error": f"Submission '{submission_id}' not found."}), 404
        return jsonify({
            "success": True,
            "message": "Submission evaluated and saved to database.",
            "data": updated
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# Priority 3: Faculty–Student Collaboration & Interventions
# ==========================================

@app.route("/api/interventions", methods=["GET"])
def list_interventions():
    """Retrieves faculty feedback, assigned support actions, and student 1-to-1 help requests."""
    _, err_resp = require_api_auth(["student", "faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        student_id = request.args.get("student_id")
        course_code = request.args.get("course_code")
        items = db_service.get_interventions(student_id=student_id, course_code=course_code)
        return jsonify({
            "success": True,
            "count": len(items),
            "data": items
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/interventions", methods=["POST"])
def create_intervention_route():
    """
    Creates a new faculty-student collaboration entry or 1-to-1 intervention request:
    - Faculty sending feedback or assigning targeted practice to a specific student
    - Student requesting 1-to-1 help or office hours for a course/weak topic
    """
    user, err_resp = require_api_auth(["student", "faculty"])
    if err_resp:
        return err_resp

    payload = dict(request.get_json(silent=True) or {})
    if str(user.get("role", "")).lower() == "student":
        payload["initiated_by"] = "student"
        payload.pop("faculty_response", None)

    student_id = payload.get("student_id")
    message = (payload.get("message") or payload.get("details") or "").strip()

    if student_id is None or not message:
        return jsonify({
            "success": False,
            "error": "'student_id' and 'message' (or 'details') are required."
        }), 400

    try:
        created = db_service.create_intervention(payload)
        return jsonify({
            "success": True,
            "message": "Collaboration record saved to database.",
            "data": created
        }), 201
    except ValueError as ve:
        status_code = 404 if "not found" in str(ve).lower() else 400
        return jsonify({"success": False, "error": str(ve)}), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/interventions/<intervention_id>/respond", methods=["POST", "PATCH", "PUT"])
def respond_intervention_route(intervention_id):
    """Allows faculty to respond to a student help request or update office-hours booking status."""
    _, err_resp = require_api_auth(["faculty"])
    if err_resp:
        return err_resp

    payload = request.get_json(silent=True) or {}
    try:
        updated = db_service.update_intervention(intervention_id, payload)
        if not updated:
            return jsonify({"success": False, "error": f"Intervention '{intervention_id}' not found."}), 404
        return jsonify({
            "success": True,
            "message": "Intervention updated in database.",
            "data": updated
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# Priority 4: Unified Course Hub Endpoints
# ==========================================

@app.route("/api/course-hub", methods=["GET"])
def get_course_hub():
    """Returns courses, faculty study materials, announcements, and assignments."""
    _, err_resp = require_api_auth(["student", "faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        course_code = request.args.get("course_code")
        student_id = request.args.get("student_id")
        courses = db_service.get_courses()
        materials = db_service.get_course_materials(course_code=course_code)
        announcements = db_service.get_announcements(course_code=course_code)
        activities = db_service.get_activities(student_id=student_id)
        return jsonify({
            "success": True,
            "data": {
                "courses": courses,
                "materials": materials,
                "announcements": announcements,
                "activities": activities
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/course-materials", methods=["GET"])
def list_course_materials():
    _, err_resp = require_api_auth(["student", "faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        course_code = request.args.get("course_code")
        materials = db_service.get_course_materials(course_code=course_code)
        return jsonify({"success": True, "count": len(materials), "data": materials}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/course-materials", methods=["POST"])
def create_course_material_route():
    _, err_resp = require_api_auth(["faculty"])
    if err_resp:
        return err_resp

    payload = request.get_json(silent=True) or {}
    try:
        created = db_service.create_course_material(payload)
        return jsonify({
            "success": True,
            "message": "Study material published to Course Hub.",
            "data": created
        }), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/announcements", methods=["GET"])
def list_announcements():
    _, err_resp = require_api_auth(["student", "faculty", "admin"])
    if err_resp:
        return err_resp
    try:
        course_code = request.args.get("course_code")
        announcements = db_service.get_announcements(course_code=course_code)
        return jsonify({"success": True, "count": len(announcements), "data": announcements}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/announcements", methods=["POST"])
def create_announcement_route():
    _, err_resp = require_api_auth(["faculty"])
    if err_resp:
        return err_resp

    payload = request.get_json(silent=True) or {}
    try:
        created = db_service.create_announcement(payload)
        return jsonify({
            "success": True,
            "message": "Course announcement published.",
            "data": created
        }), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# Priority 2: Real Admin Console Endpoints
# ==========================================

@app.route("/api/admin/overview", methods=["GET"])
def get_admin_overview():
    """
    Returns real database-backed platform governance metrics and registered user directory.
    Never fabricates user counts or fake accounts.
    """
    _, err_resp = require_api_auth(["admin"])
    if err_resp:
        return err_resp
    try:
        users = db_service.get_all_users()
        students = [u for u in users if u["role"] == "Student"]
        faculty = [u for u in users if u["role"] == "Faculty"]
        admins = [u for u in users if u["role"] == "Admin"]
        active_users = [u for u in users if u.get("status") == "Active"]
        suspended_users = [u for u in users if u.get("status") != "Active"]

        courses = db_service.get_courses()
        activities = db_service.get_activities()
        submissions = db_service.get_submissions()
        interventions = db_service.get_interventions()
        announcements = db_service.get_announcements()

        return jsonify({
            "success": True,
            "data": {
                "metrics": {
                    "total_users": len(users),
                    "students_count": len(students),
                    "faculty_count": len(faculty),
                    "admins_count": len(admins),
                    "active_users_count": len(active_users),
                    "suspended_users_count": len(suspended_users),
                    "courses_count": len(courses),
                    "activities_count": len(activities),
                    "submissions_count": len(submissions),
                    "interventions_count": len(interventions),
                    "announcements_count": len(announcements),
                    "database_connected": db_service.is_connected
                },
                "users": users
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/admin/users/status", methods=["POST", "PATCH", "PUT"])
def update_admin_user_status():
    """Allows administrators to toggle a user's account status (Active / Suspended) in Supabase."""
    _, err_resp = require_api_auth(["admin"])
    if err_resp:
        return err_resp
    payload = request.get_json(silent=True) or {}
    role = payload.get("role")
    record_id = payload.get("record_id")
    status = payload.get("status")

    if not role or record_id is None or not status:
        return jsonify({"success": False, "error": "'role', 'record_id', and 'status' are required."}), 400

    try:
        updated = db_service.update_user_status(role=role, record_id=record_id, status=status)
        if not updated:
            return jsonify({"success": False, "error": "User record not found."}), 404
        return jsonify({
            "success": True,
            "message": f"Account status updated to {status}.",
            "data": updated
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze_performance():
    """
    On-demand analytics endpoint:
    Analyzes student submissions and produces weak topics + recommendations.
    Accepts { "student_id": 1 } or { "submissions": [...] }
    """
    _, err_resp = require_api_auth(["student", "faculty", "admin"])
    if err_resp:
        return err_resp
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


@app.route("/study-assistant/chat", methods=["POST"])
@app.route("/api/study-assistant/chat", methods=["POST"])
def study_assistant_chat():
    """
    AI Study Assistant chat endpoint powered by the official Google Gen AI SDK (Gemini).
    Accepts { "message": "...", "history": [...], "previous_interaction_id": "...", "student_id": 1 }
    and returns the real Gemini-generated response.
    """
    _, err_resp = require_api_auth(["student"])
    if err_resp:
        return err_resp

    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request body must be valid JSON.",
            "error_code": "INVALID_REQUEST"
        }), 400

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({
            "success": False,
            "error": "Malformed JSON payload. Expected a JSON object.",
            "error_code": "INVALID_REQUEST"
        }), 400

    raw_message = payload.get("message")
    if not isinstance(raw_message, str) or not raw_message.strip():
        return jsonify({
            "success": False,
            "error": "Please enter a non-empty message for the AI Study Assistant.",
            "error_code": "EMPTY_MESSAGE"
        }), 400

    history = payload.get("history")
    if history is not None and not isinstance(history, list):
        return jsonify({
            "success": False,
            "error": "'history' must be a list of conversation messages.",
            "error_code": "INVALID_HISTORY"
        }), 400

    previous_interaction_id = payload.get("previous_interaction_id")
    if previous_interaction_id is not None and not isinstance(previous_interaction_id, str):
        previous_interaction_id = None

    student_context = payload.get("student_context") if isinstance(payload.get("student_context"), dict) else None
    student_id = payload.get("student_id")
    if student_context is None and student_id is not None:
        try:
            student = db_service.get_student_by_id(student_id)
            if student:
                subs = db_service.get_submissions(student_id=student["id"])
                perf = analyze_student_performance(student, subs)
                student_context = {
                    "profile": {
                        "id": student["id"],
                        "name": student["name"],
                        "course": student.get("course") or "Data Structures",
                    },
                    "metrics": {
                        "overall_score": perf["overall_score"],
                        "completion_rate": perf["completion_rate"],
                        "total_submissions": perf["total_submissions"],
                    },
                    "topic_scores": perf["topic_scores"],
                    "weak_topics": perf["weak_topics"],
                }
        except Exception:
            student_context = None

    try:
        result = generate_study_assistant_reply(
            message=raw_message,
            history=history,
            previous_interaction_id=previous_interaction_id,
            student_context=student_context,
        )
        return jsonify({
            "success": True,
            "data": result
        }), 200
    except ValueError as val_err:
        return jsonify({
            "success": False,
            "error": str(val_err),
            "error_code": "VALIDATION_ERROR"
        }), 400
    except StudyAssistantError as sa_err:
        return jsonify({
            "success": False,
            "error": str(sa_err),
            "error_code": sa_err.error_code
        }), sa_err.status_code
    except Exception:
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred while contacting the AI Study Assistant.",
            "error_code": "INTERNAL_ERROR"
        }), 500


# ==========================================
# Frontend Authentication API Compatibility
# ==========================================

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@app.route("/auth/login", methods=["POST"])
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """
    Authenticates a user by email and password against Supabase records and
    environment-configured Admin/Faculty credentials, creating a server-side session.
    """
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password."}), 400

    # Ensure environment-configured Admin/Faculty accounts are synchronized
    admin_env_email = (os.getenv("ADMIN_EMAIL") or "admin@edunexus.com").strip().lower()
    faculty_env_email = (os.getenv("FACULTY_EMAIL") or "faculty@edunexus.com").strip().lower()
    if email in (admin_env_email, faculty_env_email) and email not in db_service._password_hashes:
        db_service.ensure_configured_accounts()

    existing_user = db_service.get_user_by_email(email)
    stored_hash = db_service.get_password_hash(email)

    if not existing_user or not stored_hash or not check_password_hash(stored_hash, password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    if str(existing_user.get("status", "Active")).lower() == "suspended":
        return jsonify({"success": False, "message": "This account has been suspended by an administrator."}), 403

    role = str(existing_user.get("role", "student")).strip().lower()
    redirect_url = DASHBOARD_BY_ROLE.get(role, "/student-dashboard")

    user_data = {
        "id": existing_user.get("id"),
        "fullName": existing_user.get("fullName") or existing_user.get("name"),
        "name": existing_user.get("name") or existing_user.get("fullName"),
        "email": existing_user.get("email", email),
        "role": role,
        "department": existing_user.get("department") or "Computer Science",
        "course": existing_user.get("course") or "Data Structures"
    }

    session.clear()
    session["user"] = user_data

    return jsonify({
        "success": True,
        "message": f"Authentication successful as {role.upper()}.",
        "data": {
            "token": f"jwt_live_{int(datetime.now().timestamp())}",
            "expiresAt": int(datetime.now().timestamp()) + 86400,
            "redirectUrl": redirect_url,
            "user": user_data
        }
    }), 200


@app.route("/auth/register", methods=["POST"])
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """
    User registration endpoint:
    - Public registration only allows 'student' accounts (saved in public.students).
    - 'faculty' accounts can only be created when an authenticated Admin is logged in.
    - 'admin' registration is never permitted through the registration endpoint.
    """
    payload = request.get_json(silent=True) or {}
    full_name = (payload.get("fullName") or payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or "student").strip().lower()
    department = (payload.get("department") or "").strip() or None

    if not full_name or not email or not password or not role:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    if len(full_name) < 2:
        return jsonify({
            "success": False,
            "message": "Full name must be at least 2 characters long."
        }), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({
            "success": False,
            "message": "Please provide a valid institutional email address."
        }), 400

    if role == "admin":
        return jsonify({
            "success": False,
            "message": "Admin registration is not permitted through public portal."
        }), 403

    if role == "faculty":
        session_user = get_session_user()
        if not session_user or str(session_user.get("role", "")).lower() != "admin":
            return jsonify({
                "success": False,
                "message": "Faculty accounts must be created or approved by an administrator. Public registration is only open to students."
            }), 403

    if role not in ("student", "faculty"):
        return jsonify({
            "success": False,
            "message": "Public registration only supports the 'student' role."
        }), 403

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters long."
        }), 400

    password_hash = generate_password_hash(password)

    try:
        created_user = db_service.register_user(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role=role,
            department=department
        )
        return jsonify({
            "success": True,
            "message": "Registration successful. Please log in.",
            "data": {
                "redirectUrl": "/login",
                "user": created_user
            }
        }), 201
    except DuplicateAccountError as dup_err:
        return jsonify({
            "success": False,
            "message": str(dup_err)
        }), 409
    except ValueError as val_err:
        return jsonify({
            "success": False,
            "message": str(val_err)
        }), 400
    except RuntimeError as db_err:
        return jsonify({
            "success": False,
            "message": str(db_err)
        }), 503
    except Exception:
        return jsonify({
            "success": False,
            "message": "Database error occurred while creating the account. Registration was not saved."
        }), 500


@app.route("/auth/me", methods=["GET"])
@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Returns current authenticated session user info."""
    session_user = get_session_user()
    if not session_user:
        return jsonify({
            "success": False,
            "message": "Authentication required. Please log in."
        }), 401

    refreshed = db_service.get_user_by_email(session_user.get("email", ""))
    return jsonify({
        "success": True,
        "data": refreshed or session_user
    }), 200


@app.route("/auth/logout", methods=["POST"])
@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Invalidates the server-side Flask session."""
    session.clear()
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
    user = get_session_user()
    if not user:
        return redirect(url_for("login_view"))
    if str(user.get("role", "")).lower() != "student":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only students are authorized to access the Student Dashboard."
        }), 403
    return render_template("student-dashboard.html")


@app.route("/faculty-dashboard", methods=["GET"])
def faculty_dashboard_view():
    user = get_session_user()
    if not user:
        return redirect(url_for("login_view"))
    if str(user.get("role", "")).lower() != "faculty":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only faculty members are authorized to access the Faculty Dashboard."
        }), 403
    return render_template("faculty-dashboard.html")


@app.route("/admin-dashboard", methods=["GET"])
def admin_dashboard_view():
    user = get_session_user()
    if not user:
        return redirect(url_for("login_view"))
    if str(user.get("role", "")).lower() != "admin":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only administrators are authorized to access the Admin Dashboard."
        }), 403
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
