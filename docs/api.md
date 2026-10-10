# EduNexus AI — Backend REST API Specification

> **Tagline:** "From academic activity to actionable growth."  
> **Status:** Live Implemented REST API (Flask & Supabase PostgreSQL)  
> **Base URL:** `http://localhost:5000` (or `http://localhost:5000/api`)  
> **Deployment Target:** Render  

This document provides the complete API specification, request schemas, response formats, and error handling for all EduNexus AI endpoints.

---

## 1. System & Health

### 1.1 Health Check & Database Connectivity
- **Endpoint:** `GET /health`
- **Description:** Verifies service health, database connection state (Supabase PostgreSQL or local fallback), and course metadata.
- **Response Headers:** `Content-Type: application/json`
- **Success Response (200 OK):**
```json
{
  "status": "ok",
  "service": "EduNexus AI Backend",
  "tagline": "From academic activity to actionable growth.",
  "course": "Data Structures",
  "timestamp": "2026-10-10T11:28:00.000000+00:00",
  "database": {
    "connected": true,
    "provider": "supabase_postgresql",
    "mode": "live_database"
  }
}
```

---

## 2. Academic Core Endpoints

### 2.1 Enrolled Students Directory
- **Endpoint:** `GET /api/students`
- **Description:** Returns all enrolled students in the course cohort.
- **Success Response (200 OK):**
```json
{
  "success": true,
  "count": 4,
  "data": [
    {
      "id": 1,
      "name": "Aanya Patel",
      "email": "aanya.demo@example.com",
      "course": "Data Structures",
      "created_at": "2026-10-10T00:00:00+00:00"
    },
    {
      "id": 2,
      "name": "Rohan Shah",
      "email": "rohan.demo@example.com",
      "course": "Data Structures",
      "created_at": "2026-10-10T00:00:00+00:00"
    },
    {
      "id": 3,
      "name": "Meera Joshi",
      "email": "meera.demo@example.com",
      "course": "Data Structures",
      "created_at": "2026-10-10T00:00:00+00:00"
    },
    {
      "id": 4,
      "name": "Arjun Desai",
      "email": "arjun.demo@example.com",
      "course": "Data Structures",
      "created_at": "2026-10-10T00:00:00+00:00"
    }
  ]
}
```

---

### 2.2 Course Activities List
- **Endpoint:** `GET /api/activities`
- **Description:** Retrieves all course assessments, quizzes, labs, and exams.
- **Success Response (200 OK):**
```json
{
  "success": true,
  "count": 6,
  "data": [
    {
      "id": 1,
      "title": "Arrays & Dynamic Sizing Quiz",
      "topic": "Arrays",
      "activity_type": "Quiz",
      "max_score": 100.0
    },
    {
      "id": 2,
      "title": "Linked List Reversal Lab",
      "topic": "Linked Lists",
      "activity_type": "Lab",
      "max_score": 100.0
    },
    {
      "id": 3,
      "title": "Stack Implementation Assignment",
      "topic": "Stacks",
      "activity_type": "Assignment",
      "max_score": 100.0
    },
    {
      "id": 4,
      "title": "Queue & Circular Buffer Quiz",
      "topic": "Queues",
      "activity_type": "Quiz",
      "max_score": 100.0
    },
    {
      "id": 5,
      "title": "Recursion Depth & Backtracking Lab",
      "topic": "Recursion",
      "activity_type": "Lab",
      "max_score": 100.0
    },
    {
      "id": 6,
      "title": "Comprehensive Midterm Exam",
      "topic": "Arrays",
      "activity_type": "Exam",
      "max_score": 100.0
    }
  ]
}
```

---

### 2.3 Create Activity
- **Endpoint:** `POST /api/activities`
- **Description:** Creates a new curricular assessment.
- **Allowed Topics:** `"Arrays"`, `"Linked Lists"`, `"Stacks"`, `"Queues"`, `"Recursion"`
- **Request Body:**
```json
{
  "title": "Recursion Trees & Memoization Lab",
  "topic": "Recursion",
  "activity_type": "Lab",
  "max_score": 100.0
}
```
- **Success Response (201 Created):**
```json
{
  "success": true,
  "message": "Activity created successfully.",
  "data": {
    "id": 7,
    "title": "Recursion Trees & Memoization Lab",
    "topic": "Recursion",
    "activity_type": "Lab",
    "max_score": 100.0
  }
}
```
- **Error Responses:**
  - `400 Bad Request`: `{"success": false, "error": "Activity 'title' is required."}`
  - `400 Bad Request`: `{"success": false, "error": "Invalid topic 'Machine Learning'. Must be one of: Arrays, Linked Lists, Stacks, Queues, Recursion"}`
  - `400 Bad Request`: `{"success": false, "error": "'max_score' must be a positive number."}`

---

### 2.4 Student Academic Dashboard
- **Endpoint:** `GET /api/student/<student_id>/dashboard`
- **Description:** Computes real-time academic analytics for a student: overall score, completion rate, topic-wise mastery, deterministic weak-topic detection, and evidence-based recommendations.
- **Success Response (200 OK) for `GET /api/student/1/dashboard`:**
```json
{
  "success": true,
  "data": {
    "profile": {
      "id": 1,
      "name": "Aanya Patel",
      "email": "aanya.demo@example.com",
      "course": "Data Structures"
    },
    "metrics": {
      "overall_score": 52.3,
      "completion_rate": 50.0,
      "total_submissions": 3
    },
    "topic_scores": [
      { "topic": "Arrays", "score": 42.5, "level": "Needs Focus", "submission_count": 2, "late_count": 1 },
      { "topic": "Linked Lists", "score": 72.0, "level": "Competent", "submission_count": 1, "late_count": 0 },
      { "topic": "Stacks", "score": 0.0, "level": "Not Attempted", "submission_count": 0, "late_count": 0 },
      { "topic": "Queues", "score": 0.0, "level": "Not Attempted", "submission_count": 0, "late_count": 0 },
      { "topic": "Recursion", "score": 0.0, "level": "Not Attempted", "submission_count": 0, "late_count": 0 }
    ],
    "weak_topics": [
      {
        "topic": "Arrays",
        "score": 42.5,
        "is_flagged": true,
        "evidence": "Average score 42.5% below 50% threshold; 2 recent activity score(s) below 50% (Arrays & Dynamic Sizing Quiz: 40.0%, Comprehensive Midterm Exam: 45.0% (late submission))",
        "severity": "critical"
      }
    ],
    "recommendations": [
      {
        "topic": "Arrays",
        "score": 42.5,
        "evidence": "Average score 42.5% below 50% threshold; 2 recent activity score(s) below 50% (Arrays & Dynamic Sizing Quiz: 40.0%, Comprehensive Midterm Exam: 45.0% (late submission))",
        "recommended_action": "Complete interactive diagnostic exercises on pointer arithmetic, dynamic resizing, and boundary condition validation.",
        "resource": "EduNexus Interactive Module: Dynamic Array Memory Models & Amortized Analysis Handbook",
        "priority": "High"
      }
    ],
    "recent_submissions": [ ... ]
  }
}
```
- **Error Responses:**
  - `404 Not Found`: `{"success": false, "error": "Student with ID '999' not found."}`

---

### 2.5 Faculty Cohort Overview
- **Endpoint:** `GET /api/faculty/overview`
- **Description:** Retrieves aggregate cohort performance, class average, topic mastery distribution, and detects students needing academic support with explainable triggers and suggested interventions.
- **Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "course": "Data Structures",
    "enrolled_count": 4,
    "class_average": 53.4,
    "at_risk_count": 4,
    "topic_mastery_distribution": [
      { "topic": "Arrays", "avg_score": 52.3, "benchmark": 70.0, "mastery_status": "Attention Needed", "sample_size": 3 },
      { "topic": "Linked Lists", "avg_score": 60.0, "benchmark": 70.0, "mastery_status": "Satisfactory", "sample_size": 2 },
      { "topic": "Stacks", "avg_score": 44.0, "benchmark": 70.0, "mastery_status": "Attention Needed", "sample_size": 1 },
      { "topic": "Queues", "avg_score": 65.0, "benchmark": 70.0, "mastery_status": "Satisfactory", "sample_size": 1 },
      { "topic": "Recursion", "avg_score": 46.0, "benchmark": 70.0, "mastery_status": "Attention Needed", "sample_size": 1 }
    ],
    "at_risk_students": [
      {
        "id": 4,
        "name": "Arjun Desai",
        "email": "arjun.demo@example.com",
        "overall_score": 46.0,
        "risk_level": "High Risk",
        "risk_severity": "danger",
        "indicators": "Overall average score is 46.0%; Weak mastery in: Recursion (46.0%)",
        "weak_topics_count": 1,
        "suggested_intervention": "Schedule 1-on-1 Academic Counseling on Recursion"
      },
      {
        "id": 1,
        "name": "Aanya Patel",
        "email": "aanya.demo@example.com",
        "overall_score": 52.3,
        "risk_level": "High Risk",
        "risk_severity": "danger",
        "indicators": "Overall average score is 52.3%; Weak mastery in: Arrays (42.5%); 1 late submission(s) noted",
        "weak_topics_count": 1,
        "suggested_intervention": "Schedule 1-on-1 Academic Counseling on Arrays"
      }
    ]
  }
}
```

---

### 2.6 Record Student Submission
- **Endpoint:** `POST /api/submissions`
- **Description:** Records an assessment attempt with score and timeliness.
- **Request Body:**
```json
{
  "student_id": 1,
  "activity_id": 2,
  "score": 92.5,
  "is_late": false
}
```
- **Success Response (201 Created):**
```json
{
  "success": true,
  "message": "Submission recorded successfully.",
  "data": {
    "id": 9,
    "student_id": 1,
    "activity_id": 2,
    "score": 92.5,
    "status": "submitted"
  }
}
```
- **Error Responses:**
  - `400 Bad Request`: `{"success": false, "error": "Missing required fields: 'student_id', 'activity_id', and 'score' are required."}`
  - `400 Bad Request`: `{"success": false, "error": "Score must be a number between 0 and 100."}`
  - `404 Not Found`: `{"success": false, "error": "Student ID '999' does not exist."}`
  - `404 Not Found`: `{"success": false, "error": "Activity ID '999' does not exist."}`

---

### 2.7 On-Demand Academic Analytics
- **Endpoint:** `POST /api/analyze`
- **Description:** Runs deterministic analytics rules on demand. Accepts either an enrolled `student_id` or an ad-hoc array of submissions for hypothetical diagnostics.
- **Request Body (Option A — By Student ID):**
```json
{
  "student_id": 1
}
```
- **Request Body (Option B — By Custom Submissions):**
```json
{
  "submissions": [
    { "topic": "Recursion", "score": 38.0, "is_late": true, "activity_title": "Recursion Quiz" },
    { "topic": "Recursion", "score": 44.0, "is_late": false, "activity_title": "Recursion Lab" },
    { "topic": "Stacks", "score": 85.0, "is_late": false, "activity_title": "Stack Assignment" }
  ]
}
```
- **Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "overall_score": 55.7,
    "topic_scores": [ ... ],
    "weak_topics": [
      {
        "topic": "Recursion",
        "score": 41.0,
        "is_flagged": true,
        "evidence": "Average score 41.0% below 50% threshold; 2 recent activity score(s) below 50% (Recursion Quiz: 38.0% (late submission), Recursion Lab: 44.0%)",
        "severity": "critical"
      }
    ],
    "recommendations": [
      {
        "topic": "Recursion",
        "score": 41.0,
        "evidence": "Average score 41.0% below 50% threshold...",
        "recommended_action": "Practice call-stack execution tracing, recursive descent base cases...",
        "resource": "EduNexus Step-by-Step Recursion Visualizer & Call Stack Debugging Guide",
        "priority": "High"
      }
    ]
  }
}
```

---

## 3. Authentication & User Management Compatibility

Both `/auth/*` and `/api/auth/*` route prefixes are supported.

### 3.1 User Login
- **Endpoint:** `POST /auth/login` (alias `POST /api/auth/login`)
- **Request Body:**
```json
{
  "email": "aanya.patel@example.com",
  "password": "SecurePassword123!"
}
```
- **Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Authentication successful as STUDENT.",
  "data": {
    "token": "jwt_live_1775812800",
    "expiresAt": 1775899200,
    "user": {
      "id": "usr_12345",
      "fullName": "Aanya Patel",
      "email": "aanya.patel@example.com",
      "role": "student",
      "course": "Data Structures"
    }
  }
}
```

### 3.2 User Registration
- **Endpoint:** `POST /auth/register` (alias `POST /api/auth/register`)
- **Security Rule:** Self-registration for `admin` is rejected with `403 Forbidden`. Public registration is allowed only for `student` and `faculty`.
- **Request Body:**
```json
{
  "fullName": "Rohan Shah",
  "email": "rohan.shah@example.com",
  "password": "SecurePassword123!",
  "role": "student"
}
```
- **Success Response (201 Created):**
```json
{
  "success": true,
  "message": "Account created successfully for Rohan Shah as STUDENT.",
  "data": {
    "user": {
      "id": "usr_1775812800",
      "fullName": "Rohan Shah",
      "email": "rohan.shah@example.com",
      "role": "student",
      "createdAt": "2026-10-10T11:28:00.000000+00:00"
    }
  }
}
```

### 3.3 Active Session
- **Endpoint:** `GET /auth/me` (alias `GET /api/auth/me`)
- **Success Response (200 OK):** Current session metadata.

### 3.4 Logout
- **Endpoint:** `POST /auth/logout` (alias `POST /api/auth/logout`)
- **Success Response (200 OK):** `{"success": true, "message": "Session invalidated."}`

---

## 4. Frontend View Routes
The Flask application directly serves the frontend pages:
- `GET /` — Platform Landing / Portal Index
- `GET /login` — Login Page
- `GET /register` — Registration Page
- `GET /student-dashboard` — Student Dashboard
- `GET /faculty-dashboard` — Faculty Dashboard
- `GET /admin-dashboard` — Administrator Dashboard
