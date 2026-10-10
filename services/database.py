"""
EduNexus AI — Database Access Service
Connects to Supabase PostgreSQL with graceful fallback to local mock_data.json.
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"
MOCK_FILE_PATH = BASE_DIR / "mock_data.json"

# Load environment variables explicitly from project root .env
load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)


@dataclass
class _PostgRESTResponse:
    """Normalized response object matching supabase-py execute() return signature."""
    data: List[Dict[str, Any]]


class _PostgRESTTableQuery:
    """Chainable PostgREST query builder using Python standard library urllib."""

    def __init__(self, base_url: str, api_key: str, table_name: str):
        self.endpoint = f"{base_url.rstrip('/')}/rest/v1/{table_name}"
        self.api_key = api_key
        self._method = "GET"
        self._select_cols = "*"
        self._filters: List[tuple] = []
        self._order_by: Optional[str] = None
        self._limit_val: Optional[int] = None
        self._payload: Optional[Dict[str, Any]] = None

    def select(self, columns: str = "*") -> "_PostgRESTTableQuery":
        self._method = "GET"
        # PostgREST expects no spaces around commas in embedded resource selects
        self._select_cols = ",".join(part.strip() for part in columns.split(","))
        return self

    def eq(self, column: str, value: Any) -> "_PostgRESTTableQuery":
        self._filters.append((column, f"eq.{value}"))
        return self

    def order(self, column: str, desc: bool = False) -> "_PostgRESTTableQuery":
        direction = "desc" if desc else "asc"
        self._order_by = f"{column}.{direction}"
        return self

    def limit(self, count: int) -> "_PostgRESTTableQuery":
        self._limit_val = int(count)
        return self

    def insert(self, payload: Dict[str, Any]) -> "_PostgRESTTableQuery":
        self._method = "POST"
        self._payload = payload
        return self

    def execute(self) -> _PostgRESTResponse:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self._method == "POST":
            headers["Prefer"] = "return=representation"
            body = json.dumps(self._payload or {}).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint, data=body, headers=headers, method="POST"
            )
        else:
            params: List[tuple] = [("select", self._select_cols)]
            params.extend(self._filters)
            if self._order_by:
                params.append(("order", self._order_by))
            if self._limit_val is not None:
                params.append(("limit", str(self._limit_val)))
            query_string = urllib.parse.urlencode(params, safe="(),.*")
            url = f"{self.endpoint}?{query_string}"
            req = urllib.request.Request(url, headers=headers, method="GET")

        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else []
            if isinstance(parsed, dict):
                parsed = [parsed]
            return _PostgRESTResponse(data=parsed)


class PostgRESTClient:
    """Lightweight Supabase PostgREST client requiring zero third-party packages."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url.rstrip("/")
        self.supabase_key = supabase_key

    def table(self, table_name: str) -> _PostgRESTTableQuery:
        return _PostgRESTTableQuery(self.supabase_url, self.supabase_key, table_name)


def _clean_env_value(val: Optional[str]) -> str:
    """Strips whitespace and surrounding quotes from an environment variable value."""
    if not val:
        return ""
    cleaned = val.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
        cleaned = cleaned[1:-1].strip()
    return cleaned


class DuplicateAccountError(ValueError):
    """Raised when attempting to register an email address that already exists."""
    pass


class DatabaseService:
    def __init__(self):
        self.supabase_url = ""
        self.supabase_key = ""
        self.client = None
        self.client_driver = "mock_fallback"
        self.is_connected = False
        self.failure_category: Optional[str] = None
        self.diagnostic_message: str = "Not initialized"
        self.verified_table: Optional[str] = None
        self._mock_data = None
        self._password_hashes: Dict[str, str] = {}

        self._init_connection()

    def _load_credentials(self) -> None:
        """Reloads .env from project root and extracts normalized Supabase credentials."""
        if ENV_FILE_PATH.exists():
            load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
        else:
            load_dotenv(override=True)

        raw_url = (
            os.getenv("SUPABASE_URL")
            or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
            or os.getenv("VITE_SUPABASE_URL")
            or ""
        )
        raw_key = (
            os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
            or ""
        )

        self.supabase_url = _clean_env_value(raw_url).rstrip("/")
        self.supabase_key = _clean_env_value(raw_key)

    def _sanitize_error(self, err: Exception) -> str:
        """Scrubs any credential values from error messages before logging/reporting."""
        msg = str(err)
        if self.supabase_key and len(self.supabase_key) > 4:
            msg = msg.replace(self.supabase_key, "[REDACTED_KEY]")
        return msg[:240]

    def _classify_error(self, err: Exception) -> tuple[str, str]:
        """Classifies an exception into a safe failure category and diagnostic summary."""
        safe_msg = self._sanitize_error(err)
        lower_msg = safe_msg.lower()

        if isinstance(err, urllib.error.HTTPError):
            code = err.code
            try:
                err_body = err.read().decode("utf-8", errors="ignore")
                if self.supabase_key and len(self.supabase_key) > 4:
                    err_body = err_body.replace(self.supabase_key, "[REDACTED_KEY]")
                lower_body = err_body.lower()
            except Exception:
                lower_body = ""

            if code in (401, 403) or "invalid api key" in lower_body or "jwt" in lower_body:
                return (
                    "auth_or_key_error",
                    f"Supabase rejected the API key (HTTP {code}). Verify SUPABASE_KEY in .env."
                )
            if code == 404 or "42p01" in lower_body or "pgrst" in lower_body or "42501" in lower_body:
                return (
                    "missing_table_or_rls",
                    f"Table 'students' not accessible (HTTP {code}). Check schema creation or RLS policies."
                )
            return ("api_http_error", f"Supabase REST API returned HTTP {code}.")

        if "401" in lower_msg or "403" in lower_msg or "invalid api key" in lower_msg or "jwt" in lower_msg:
            return (
                "auth_or_key_error",
                "Authentication failed: SUPABASE_KEY is invalid, expired, or unauthorized."
            )
        if "42p01" in lower_msg or "relation" in lower_msg or "does not exist" in lower_msg:
            return (
                "missing_table_or_rls",
                "Database table 'students' does not exist in the public schema."
            )
        if "42501" in lower_msg or "row-level security" in lower_msg or "permission denied" in lower_msg:
            return (
                "missing_table_or_rls",
                "Row-Level Security (RLS) or table permissions blocked access to 'students'."
            )
        if (
            isinstance(err, urllib.error.URLError)
            or "getaddrinfo" in lower_msg
            or "connect" in lower_msg
            or "timeout" in lower_msg
            or "timed out" in lower_msg
            or "network" in lower_msg
            or "ssl" in lower_msg
        ):
            return (
                "network_error",
                f"Network error connecting to Supabase project URL ({safe_msg})."
            )

        return ("client_init_error", f"Database connection error: {safe_msg}")

    def _init_connection(self) -> bool:
        """Attempts to initialize the Supabase client and verify read access."""
        self._load_credentials()

        # 1. Check missing environment variables
        if not self.supabase_url or not self.supabase_key:
            self.is_connected = False
            self.client = None
            self.client_driver = "mock_fallback"
            self.verified_table = None
            self.failure_category = "missing_env_vars"
            missing = []
            if not self.supabase_url:
                missing.append("SUPABASE_URL")
            if not self.supabase_key:
                missing.append("SUPABASE_KEY")
            env_hint = "found .env file" if ENV_FILE_PATH.exists() else "no .env file found in project root"
            self.diagnostic_message = (
                f"Missing required environment variable(s): {', '.join(missing)} ({env_hint}). "
                "Using local mock fallback."
            )
            return False

        # 2. Check placeholder credentials from .env.example
        if (
            self.supabase_url.startswith("https://your-project")
            or "your-anon-or-service-role-key" in self.supabase_key
        ):
            self.is_connected = False
            self.client = None
            self.client_driver = "mock_fallback"
            self.verified_table = None
            self.failure_category = "placeholder_credentials"
            self.diagnostic_message = (
                "SUPABASE_URL or SUPABASE_KEY still contains placeholder values from .env.example. "
                "Replace them with your real Supabase project credentials."
            )
            return False

        # 3. Validate URL format
        parsed_url = urllib.parse.urlparse(self.supabase_url)
        if parsed_url.scheme not in ("https", "http") or not parsed_url.netloc:
            self.is_connected = False
            self.client = None
            self.client_driver = "mock_fallback"
            self.verified_table = None
            self.failure_category = "invalid_url"
            self.diagnostic_message = (
                "SUPABASE_URL is not a valid HTTP/HTTPS URL (expected https://<project_ref>.supabase.co)."
            )
            return False

        # 4. Initialize client (try official supabase-py SDK first, then PostgREST HTTP client)
        candidate_clients = []
        try:
            from supabase import create_client
            sdk_client = create_client(self.supabase_url, self.supabase_key)
            candidate_clients.append(("supabase_sdk", sdk_client))
        except Exception:
            # If supabase SDK is not installed in the active Python environment
            # or encounters httpx/gotrue version incompatibility, fall back to PostgREST HTTP
            pass

        candidate_clients.append(
            ("postgrest_http", PostgRESTClient(self.supabase_url, self.supabase_key))
        )

        last_exception: Optional[Exception] = None
        for driver_name, candidate in candidate_clients:
            try:
                res = candidate.table("students").select("id").limit(1).execute()
                if hasattr(res, "data") and isinstance(res.data, list):
                    self.client = candidate
                    self.client_driver = driver_name
                    self.is_connected = True
                    self.failure_category = None
                    self.verified_table = "students"
                    self.diagnostic_message = (
                        f"Connected to Supabase PostgreSQL via {driver_name} "
                        "(verified read access on 'students' table)."
                    )
                    return True
            except Exception as err:
                last_exception = err

        # 5. All candidate drivers failed — classify the failure safely
        self.is_connected = False
        self.client = None
        self.client_driver = "mock_fallback"
        self.verified_table = None
        if last_exception is not None:
            self.failure_category, self.diagnostic_message = self._classify_error(last_exception)
        else:
            self.failure_category = "client_init_error"
            self.diagnostic_message = "Unable to initialize Supabase client."
        return False

    def _ensure_connection(self) -> bool:
        """Re-attempts connection if currently disconnected."""
        if not self.is_connected or self.client is None:
            return self._init_connection()
        return True

    def _is_testing_mode(self) -> bool:
        """Checks if Flask app is currently running inside automated unit tests."""
        try:
            from flask import has_app_context, current_app
            return bool(has_app_context() and current_app.config.get("TESTING"))
        except Exception:
            return False

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
        """Returns database connectivity, operational mode, and safe diagnostics."""
        self._ensure_connection()
        return {
            "connected": self.is_connected,
            "provider": "supabase_postgresql" if self.is_connected else "local_mock_fallback",
            "mode": "live_database" if self.is_connected else "read_only_mock",
            "diagnostics": {
                "driver": self.client_driver,
                "env_file_exists": ENV_FILE_PATH.exists(),
                "url_configured": bool(
                    self.supabase_url and not self.supabase_url.startswith("https://your-project")
                ),
                "key_configured": bool(
                    self.supabase_key and "your-anon-or-service-role-key" not in self.supabase_key
                ),
                "verified_table": self.verified_table,
                "failure_category": self.failure_category,
                "message": self.diagnostic_message
            }
        }

    # ==========================================
    # Students API
    # ==========================================
    def get_students(self) -> List[Dict[str, Any]]:
        """Fetch all enrolled students."""
        if self._ensure_connection() and self.client:
            try:
                res = self.client.table("students").select("*").order("id").execute()
                if res.data is not None:
                    return res.data
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

        if self._ensure_connection() and self.client:
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

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Look up an existing student or faculty account by email address."""
        clean_email = (email or "").strip().lower()
        if not clean_email:
            return None

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                std_res = self.client.table("students").select("*").eq("email", clean_email).execute()
                if std_res.data and len(std_res.data) > 0:
                    row = std_res.data[0]
                    return {
                        "id": row.get("id"),
                        "fullName": row.get("name"),
                        "name": row.get("name"),
                        "email": row.get("email"),
                        "role": "student",
                        "table": "students",
                        "createdAt": row.get("created_at")
                    }
            except Exception:
                pass

            try:
                fac_res = self.client.table("faculty").select("*").eq("email", clean_email).execute()
                if fac_res.data and len(fac_res.data) > 0:
                    row = fac_res.data[0]
                    return {
                        "id": row.get("id"),
                        "fullName": row.get("full_name"),
                        "name": row.get("full_name"),
                        "email": row.get("email"),
                        "role": "faculty",
                        "department": row.get("department"),
                        "table": "faculty",
                        "createdAt": row.get("created_at")
                    }
            except Exception:
                pass
            return None

        # Testing mode lookup in mock store
        for s in self._get_mock_data().get("students", []):
            if str(s.get("email", "")).strip().lower() == clean_email:
                return {
                    "id": s.get("id"),
                    "fullName": s.get("name"),
                    "name": s.get("name"),
                    "email": s.get("email"),
                    "role": "student",
                    "table": "students",
                    "createdAt": s.get("created_at")
                }
        for f in self._get_mock_data().get("faculty", []):
            if str(f.get("email", "")).strip().lower() == clean_email:
                return {
                    "id": f.get("id"),
                    "fullName": f.get("full_name"),
                    "name": f.get("full_name"),
                    "email": f.get("email"),
                    "role": "faculty",
                    "table": "faculty",
                    "createdAt": f.get("created_at")
                }
        return None

    def get_password_hash(self, email: str) -> Optional[str]:
        """Retrieves the stored password hash for an email if registered in this session."""
        clean_email = (email or "").strip().lower()
        return self._password_hashes.get(clean_email)

    def register_user(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        role: str,
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Persists a newly registered Student or Faculty account into Supabase PostgreSQL.
        - Students are inserted into public.students (name, email).
        - Faculty are inserted into public.faculty (full_name, email, department).
        - Raises DuplicateAccountError if the email is already registered.
        - Raises RuntimeError if the database connection or insert fails.
        """
        clean_name = (full_name or "").strip()
        clean_email = (email or "").strip().lower()
        clean_role = (role or "").strip().lower()

        if not clean_name or not clean_email or not password_hash:
            raise ValueError("Full name, email, and password hash are required.")
        if clean_role not in ("student", "faculty"):
            raise ValueError("Role must be 'student' or 'faculty'.")

        # 1. Check for duplicate email before inserting
        existing = self.get_user_by_email(clean_email)
        if existing is not None:
            raise DuplicateAccountError(f"An account with email '{clean_email}' is already registered.")

        # 2. Automated test mode (isolated from live Supabase mutations)
        if self._is_testing_mode():
            now_iso = datetime.now(timezone.utc).isoformat()
            if clean_role == "student":
                students_list = self._get_mock_data().setdefault("students", [])
                new_id = max([int(s.get("id", 0)) for s in students_list] + [0]) + 1
                record = {"id": new_id, "name": clean_name, "email": clean_email, "created_at": now_iso}
                students_list.append(record)
                self._password_hashes[clean_email] = password_hash
                return {
                    "id": new_id,
                    "fullName": clean_name,
                    "name": clean_name,
                    "email": clean_email,
                    "role": "student",
                    "table": "students",
                    "createdAt": now_iso
                }
            else:
                faculty_list = self._get_mock_data().setdefault("faculty", [])
                new_id = max([int(f.get("id", 0)) for f in faculty_list] + [0]) + 1
                record = {
                    "id": new_id,
                    "full_name": clean_name,
                    "email": clean_email,
                    "department": department or "Computer Science",
                    "created_at": now_iso
                }
                faculty_list.append(record)
                self._password_hashes[clean_email] = password_hash
                return {
                    "id": new_id,
                    "fullName": clean_name,
                    "name": clean_name,
                    "email": clean_email,
                    "role": "faculty",
                    "table": "faculty",
                    "createdAt": now_iso
                }

        # 3. Live Supabase PostgreSQL insert (never falls back to mock data)
        if not self._ensure_connection() or not self.client:
            raise RuntimeError(
                "Database connection is unavailable. Account could not be saved to Supabase PostgreSQL."
            )

        try:
            if clean_role == "student":
                payload = {"name": clean_name, "email": clean_email}
                res = self.client.table("students").insert(payload).execute()
                if not res.data or len(res.data) == 0:
                    raise RuntimeError("Supabase insert into 'students' returned no record.")
                inserted = res.data[0]
                self._password_hashes[clean_email] = password_hash
                return {
                    "id": inserted.get("id"),
                    "fullName": inserted.get("name", clean_name),
                    "name": inserted.get("name", clean_name),
                    "email": inserted.get("email", clean_email),
                    "role": "student",
                    "table": "students",
                    "createdAt": inserted.get("created_at") or datetime.now(timezone.utc).isoformat()
                }
            else:
                payload = {
                    "full_name": clean_name,
                    "email": clean_email,
                    "department": department or "Computer Science"
                }
                res = self.client.table("faculty").insert(payload).execute()
                if not res.data or len(res.data) == 0:
                    raise RuntimeError("Supabase insert into 'faculty' returned no record.")
                inserted = res.data[0]
                self._password_hashes[clean_email] = password_hash
                return {
                    "id": inserted.get("id"),
                    "fullName": inserted.get("full_name", clean_name),
                    "name": inserted.get("full_name", clean_name),
                    "email": inserted.get("email", clean_email),
                    "role": "faculty",
                    "table": "faculty",
                    "createdAt": inserted.get("created_at") or datetime.now(timezone.utc).isoformat()
                }
        except DuplicateAccountError:
            raise
        except urllib.error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8", errors="ignore").lower()
            except Exception:
                pass
            if http_err.code == 409 or "23505" in err_body or "duplicate" in err_body or "unique" in err_body:
                raise DuplicateAccountError(f"An account with email '{clean_email}' is already registered.")
            raise RuntimeError(f"Supabase database error (HTTP {http_err.code}) while saving account.")
        except Exception as err:
            safe_msg = self._sanitize_error(err)
            lower_msg = safe_msg.lower()
            if "23505" in lower_msg or "duplicate key" in lower_msg or "unique constraint" in lower_msg or "409" in lower_msg:
                raise DuplicateAccountError(f"An account with email '{clean_email}' is already registered.")
            raise RuntimeError(f"Failed to save account to Supabase: {safe_msg}")

    # ==========================================
    # Activities API
    # ==========================================
    def get_activities(self) -> List[Dict[str, Any]]:
        """Fetch all course activities."""
        if self._ensure_connection() and self.client:
            try:
                res = self.client.table("activities").select("*").order("id").execute()
                if res.data is not None:
                    return res.data
            except Exception:
                pass
        return self._get_mock_data().get("activities", [])

    def get_activity_by_id(self, activity_id: Any) -> Optional[Dict[str, Any]]:
        """Fetch single activity by ID."""
        try:
            numeric_id = int(activity_id)
        except (ValueError, TypeError):
            numeric_id = activity_id

        if self._ensure_connection() and self.client:
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

        if self._ensure_connection() and self.client and not self._is_testing_mode():
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
        if self._ensure_connection() and self.client:
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

        if self._ensure_connection() and self.client and not self._is_testing_mode():
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
