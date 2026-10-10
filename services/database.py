"""
EduNexus AI — Database Access Service
Connects to Supabase PostgreSQL with graceful fallback to local mock_data.json.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_FILE_PATH = BASE_DIR / "mock_data.json"


class DatabaseService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "").strip()
        self.supabase_key = os.getenv("SUPABASE_KEY", "").strip()
        self.client = None
        self.is_connected = False
        self._mock_data = None

        self._init_connection()

    def _init_connection(self):
        """Attempts to initialize the Supabase client."""
        if self.supabase_url and self.supabase_key and not self.supabase_url.startswith("https://your-project"):
            try:
                from supabase import create_client
                self.client = create_client(self.supabase_url, self.supabase_key)
                # Quick health check probe
                res = self.client.table("students").select("id").limit(1).execute()
                self.is_connected = True
            except Exception as e:
                self.is_connected = False
                self.client = None
        else:
            self.is_connected = False
            self.client = None

    def _get_mock_data(self) -> Dict[str, Any]:
        """Loads synthetic records from mock_data.json as a fallback."""
        if self._mock_data is None:
            if MOCK_FILE_PATH.exists():
                with open(MOCK_FILE_PATH, "r", encoding="utf-8") as f:
                    self._mock_data = json.load(f)
            else:
                self._mock_data = {
                    "course": "Data Structures",
                    "topics": ["Arrays", "Linked Lists", "Stacks", "Queues", "Recursion"],
                    "students": [],
                    "activities": [],
                    "submissions": []
                }
        return self._mock_data

    def get_status(self) -> Dict[str, Any]:
        """Returns database connectivity and operational mode."""
        return {
            "connected": self.is_connected,
            "provider": "supabase_postgresql" if self.is_connected else "local_mock_fallback",
            "mode": "live_database" if self.is_connected else "read_only_mock"
        }

    # ==========================================
    # Students API
    # ==========================================
    def get_students(self) -> List[Dict[str, Any]]:
        """Fetch all enrolled students."""
        if self.is_connected and self.client:
            try:
                res = self.client.table("students").select("*").order("id").execute()
                return res.data or []
            except Exception:
                pass
        # Mock fallback
        return self._get_mock_data().get("students", [])

    def get_student_by_id(self, student_id: Any) -> Optional[Dict[str, Any]]:
        """Fetch single student by ID."""
        try:
            numeric_id = int(student_id)
        except (ValueError, TypeError):
            numeric_id = student_id

        if self.is_connected and self.client:
            try:
                res = self.client.table("students").select("*").eq("id", numeric_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        # Mock fallback
        for s in self._get_mock_data().get("students", []):
            if str(s.get("id")) == str(student_id):
                return s
        return None

    # ==========================================
    # Activities API
    # ==========================================
    def get_activities(self) -> List[Dict[str, Any]]:
        """Fetch all course activities."""
        if self.is_connected and self.client:
            try:
                res = self.client.table("activities").select("*").order("id").execute()
                return res.data or []
            except Exception:
                pass
        return self._get_mock_data().get("activities", [])

    def get_activity_by_id(self, activity_id: Any) -> Optional[Dict[str, Any]]:
        """Fetch single activity by ID."""
        try:
            numeric_id = int(activity_id)
        except (ValueError, TypeError):
            numeric_id = activity_id

        if self.is_connected and self.client:
            try:
                res = self.client.table("activities").select("*").eq("id", numeric_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        for a in self._get_mock_data().get("activities", []):
            if str(a.get("id")) == str(activity_id):
                return a
        return None

    def create_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new activity. Writes to Supabase or appends to mock dataset."""
        payload = {
            "title": activity_data["title"],
            "topic": activity_data["topic"],
            "activity_type": activity_data.get("activity_type", "Quiz"),
            "max_score": float(activity_data.get("max_score", 100))
        }

        if self.is_connected and self.client:
            try:
                res = self.client.table("activities").insert(payload).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        # In-memory mock fallback
        mock_id = len(self._get_mock_data().get("activities", [])) + 1
        new_record = {"id": mock_id, **payload}
        self._get_mock_data().setdefault("activities", []).append(new_record)
        return new_record

    # ==========================================
    # Submissions API
    # ==========================================
    def get_submissions(self, student_id: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Fetch submissions, optionally filtered by student_id with activity details."""
        if self.is_connected and self.client:
            try:
                # Query submissions joined with activities
                query = self.client.table("submissions").select("*, activities(*)")
                if student_id is not None:
                    try:
                        numeric_id = int(student_id)
                    except (ValueError, TypeError):
                        numeric_id = student_id
                    query = query.eq("student_id", numeric_id)
                res = query.order("submitted_at", desc=True).execute()
                
                # Normalize join format
                submissions = []
                for sub in res.data or []:
                    act = sub.get("activities") or {}
                    submissions.append({
                        "id": sub.get("id"),
                        "student_id": sub.get("student_id"),
                        "activity_id": sub.get("activity_id"),
                        "score": float(sub.get("score", 0)),
                        "status": sub.get("status", "submitted"),
                        "is_late": sub.get("status") == "late",
                        "submitted_at": sub.get("submitted_at"),
                        "activity_title": act.get("title", f"Activity {sub.get('activity_id')}"),
                        "topic": act.get("topic", "General"),
                        "max_score": float(act.get("max_score", 100))
                    })
                return submissions
            except Exception:
                pass

        # Fallback to mock data with join
        raw_submissions = self._get_mock_data().get("submissions", [])
        activities_map = {a["id"]: a for a in self._get_mock_data().get("activities", [])}

        normalized = []
        for sub in raw_submissions:
            if student_id is not None and str(sub.get("student_id")) != str(student_id):
                continue
            act = activities_map.get(sub.get("activity_id"), {})
            normalized.append({
                "id": sub.get("id"),
                "student_id": sub.get("student_id"),
                "activity_id": sub.get("activity_id"),
                "score": float(sub.get("score", 0)),
                "status": sub.get("status", "submitted"),
                "is_late": sub.get("status") == "late",
                "submitted_at": sub.get("submitted_at"),
                "activity_title": act.get("title", f"Activity {sub.get('activity_id')}"),
                "topic": act.get("topic", "General"),
                "max_score": float(act.get("max_score", 100))
            })
        return normalized

    def create_submission(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a student submission. Writes to Supabase or appends to mock dataset."""
        status = "late" if submission_data.get("is_late") else submission_data.get("status", "submitted")

        payload = {
            "student_id": int(submission_data["student_id"]),
            "activity_id": int(submission_data["activity_id"]),
            "score": float(submission_data["score"]),
            "status": status
        }

        if self.is_connected and self.client:
            try:
                res = self.client.table("submissions").insert(payload).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        # In-memory mock fallback
        mock_id = len(self._get_mock_data().get("submissions", [])) + 1
        new_record = {
            "id": mock_id,
            **payload,
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        self._get_mock_data().setdefault("submissions", []).append(new_record)
        return new_record


# Singleton instance
db_service = DatabaseService()
