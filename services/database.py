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
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"
MOCK_FILE_PATH = BASE_DIR / "mock_data.json"

# Load environment variables explicitly from project root .env
load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)


def _strip_sensitive_fields(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Removes sensitive columns such as password_hash before returning records."""
    if not isinstance(row, dict):
        return row
    return {k: v for k, v in row.items() if k not in ("password_hash", "password")}


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

    def update(self, payload: Dict[str, Any]) -> "_PostgRESTTableQuery":
        self._method = "PATCH"
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
        elif self._method == "PATCH":
            headers["Prefer"] = "return=representation"
            query_string = urllib.parse.urlencode(self._filters, safe="(),.*")
            url = f"{self.endpoint}?{query_string}" if query_string else self.endpoint
            body = json.dumps(self._payload or {}).encode("utf-8")
            req = urllib.request.Request(
                url, data=body, headers=headers, method="PATCH"
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
        self.ensure_configured_accounts()

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

        candidate_clients = []
        try:
            from supabase import create_client
            sdk_client = create_client(self.supabase_url, self.supabase_key)
            candidate_clients.append(("supabase_sdk", sdk_client))
        except Exception:
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

    def _sync_mock_configured_accounts(self) -> None:
        """Ensures configured ADMIN_EMAIL and FACULTY_EMAIL exist in the in-memory mock store with hashed passwords."""
        if self._mock_data is None:
            return

        admin_email = _clean_env_value(os.getenv("ADMIN_EMAIL") or "admin@edunexus.com").lower()
        admin_password = _clean_env_value(os.getenv("ADMIN_PASSWORD") or os.getenv("EDUNEXUS_ADMIN_PASSWORD") or "")
        faculty_email = _clean_env_value(os.getenv("FACULTY_EMAIL") or "faculty@edunexus.com").lower()
        faculty_password = _clean_env_value(os.getenv("FACULTY_PASSWORD") or "")

        if admin_email and admin_password:
            if admin_email not in self._password_hashes:
                self._password_hashes[admin_email] = generate_password_hash(admin_password)
            admins_list = self._mock_data.setdefault("admins", [])
            existing_adm = next(
                (a for a in admins_list if str(a.get("email", "")).strip().lower() == admin_email),
                None
            )
            if existing_adm is None:
                new_id = max([int(a.get("id", 0)) for a in admins_list] + [0]) + 1
                admins_list.append({
                    "id": new_id,
                    "full_name": "System Administrator",
                    "email": admin_email,
                    "status": "Active",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

        if faculty_email and faculty_password:
            if faculty_email not in self._password_hashes:
                self._password_hashes[faculty_email] = generate_password_hash(faculty_password)
            faculty_list = self._mock_data.setdefault("faculty", [])
            existing_fac = next(
                (f for f in faculty_list if str(f.get("email", "")).strip().lower() == faculty_email),
                None
            )
            if existing_fac is None:
                new_id = max([int(f.get("id", 0)) for f in faculty_list] + [0]) + 1
                faculty_list.append({
                    "id": new_id,
                    "full_name": "Dr. Sarah Mitchell",
                    "email": faculty_email,
                    "department": "Computer Science",
                    "status": "Active",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

    def ensure_configured_accounts(self) -> None:
        """
        Ensures the environment-configured Admin (ADMIN_EMAIL / ADMIN_PASSWORD)
        and Faculty (FACULTY_EMAIL / FACULTY_PASSWORD) accounts exist in Supabase
        with secure password hashes and without creating duplicate records.
        """
        self._load_credentials()
        admin_email = _clean_env_value(os.getenv("ADMIN_EMAIL") or "admin@edunexus.com").lower()
        admin_password = _clean_env_value(os.getenv("ADMIN_PASSWORD") or os.getenv("EDUNEXUS_ADMIN_PASSWORD") or "")
        faculty_email = _clean_env_value(os.getenv("FACULTY_EMAIL") or "faculty@edunexus.com").lower()
        faculty_password = _clean_env_value(os.getenv("FACULTY_PASSWORD") or "")

        if admin_email and admin_password:
            admin_hash = generate_password_hash(admin_password)
            self._password_hashes[admin_email] = admin_hash
        else:
            admin_hash = None

        if faculty_email and faculty_password:
            faculty_hash = generate_password_hash(faculty_password)
            self._password_hashes[faculty_email] = faculty_hash
        else:
            faculty_hash = None

        self._get_mock_data()
        self._sync_mock_configured_accounts()

        if not self._ensure_connection() or not self.client or self._is_testing_mode():
            return

        if admin_email and admin_hash:
            try:
                adm_res = self.client.table("admins").select("*").eq("email", admin_email).execute()
                if adm_res.data and len(adm_res.data) > 0:
                    row = adm_res.data[0]
                    self.client.table("admins").update({
                        "password_hash": admin_hash,
                        "status": row.get("status") or "Active"
                    }).eq("id", row["id"]).execute()
                else:
                    self.client.table("admins").insert({
                        "full_name": "System Administrator",
                        "email": admin_email,
                        "password_hash": admin_hash,
                        "status": "Active"
                    }).execute()
            except Exception:
                pass

        if faculty_email and faculty_hash:
            try:
                fac_res = self.client.table("faculty").select("*").eq("email", faculty_email).execute()
                if fac_res.data and len(fac_res.data) > 0:
                    row = fac_res.data[0]
                    self.client.table("faculty").update({
                        "password_hash": faculty_hash,
                        "status": row.get("status") or "Active"
                    }).eq("id", row["id"]).execute()
                else:
                    self.client.table("faculty").insert({
                        "full_name": "Dr. Sarah Mitchell",
                        "email": faculty_email,
                        "department": "Computer Science",
                        "password_hash": faculty_hash,
                        "status": "Active"
                    }).execute()
            except Exception:
                pass

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
                    "faculty": [],
                    "admins": [],
                    "courses": [{"id": 1, "course_name": "Data Structures & Algorithms", "course_code": "CS-301"}],
                    "activities": [],
                    "submissions": [],
                    "course_materials": [],
                    "announcements": [],
                    "interventions": []
                }
            self._sync_mock_configured_accounts()
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
    # Students, Faculty & Admin User Directory
    # ==========================================
    def get_students(self) -> List[Dict[str, Any]]:
        """Fetch all enrolled students without exposing password hashes."""
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("students").select("*").order("id").execute()
                if res.data is not None:
                    return [_strip_sensitive_fields(r) for r in res.data]
            except Exception:
                pass
        return [_strip_sensitive_fields(r) for r in self._get_mock_data().get("students", [])]

    def get_student_by_id(self, student_id: Any) -> Optional[Dict[str, Any]]:
        """Fetch single student by ID without exposing password hash."""
        try:
            numeric_id = int(student_id)
        except (ValueError, TypeError):
            numeric_id = student_id

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("students").select("*").eq("id", numeric_id).execute()
                if res.data and len(res.data) > 0:
                    return _strip_sensitive_fields(res.data[0])
            except Exception:
                pass

        for s in self._get_mock_data().get("students", []):
            if str(s.get("id")) == str(student_id):
                return _strip_sensitive_fields(s)
        return None

    def get_faculty(self) -> List[Dict[str, Any]]:
        """Fetch all registered faculty members without exposing password hashes."""
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("faculty").select("*").order("id").execute()
                if res.data is not None:
                    return [_strip_sensitive_fields(r) for r in res.data]
            except Exception:
                pass
        return [_strip_sensitive_fields(r) for r in self._get_mock_data().get("faculty", [])]

    def get_faculty_by_id(self, faculty_id: Any) -> Optional[Dict[str, Any]]:
        """Fetch single faculty member by ID."""
        try:
            numeric_id = int(faculty_id)
        except (ValueError, TypeError):
            numeric_id = faculty_id

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("faculty").select("*").eq("id", numeric_id).execute()
                if res.data and len(res.data) > 0:
                    return _strip_sensitive_fields(res.data[0])
            except Exception:
                pass

        for f in self._get_mock_data().get("faculty", []):
            if str(f.get("id")) == str(faculty_id):
                return _strip_sensitive_fields(f)
        return None

    def get_admins(self) -> List[Dict[str, Any]]:
        """Fetch all administrator accounts without exposing password hashes."""
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("admins").select("*").order("id").execute()
                if res.data is not None:
                    return [_strip_sensitive_fields(r) for r in res.data]
            except Exception:
                pass
        return [_strip_sensitive_fields(r) for r in self._get_mock_data().get("admins", [])]

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Returns combined real user directory across students, faculty, and admins."""
        users: List[Dict[str, Any]] = []
        students = self.get_students()
        faculty_list = self.get_faculty()
        admins_list = self.get_admins()

        for s in students:
            users.append({
                "id": f"student_{s.get('id')}",
                "record_id": s.get("id"),
                "table": "students",
                "name": s.get("name") or "Student",
                "email": s.get("email") or "",
                "role": "Student",
                "department": s.get("course") or "Data Structures",
                "status": s.get("status") or "Active",
                "created_at": s.get("created_at")
            })

        for f in faculty_list:
            users.append({
                "id": f"faculty_{f.get('id')}",
                "record_id": f.get("id"),
                "table": "faculty",
                "name": f.get("full_name") or f.get("name") or "Faculty",
                "email": f.get("email") or "",
                "role": "Faculty",
                "department": f.get("department") or "Computer Science",
                "status": f.get("status") or "Active",
                "created_at": f.get("created_at")
            })

        for a in admins_list:
            users.append({
                "id": f"admin_{a.get('id')}",
                "record_id": a.get("id"),
                "table": "admins",
                "name": a.get("full_name") or a.get("name") or "Administrator",
                "email": a.get("email") or "",
                "role": "Admin",
                "department": "Global Institution",
                "status": a.get("status") or "Active",
                "created_at": a.get("created_at")
            })

        return users

    def update_user_status(self, role: str, record_id: Any, status: str) -> Optional[Dict[str, Any]]:
        """Updates account status (Active / Suspended) in the corresponding role table."""
        clean_role = (role or "").strip().lower()
        table_map = {
            "student": "students",
            "students": "students",
            "faculty": "faculty",
            "admin": "admins",
            "admins": "admins"
        }
        table_name = table_map.get(clean_role)
        if not table_name:
            raise ValueError(f"Unsupported role '{role}'.")

        clean_status = "Suspended" if str(status).lower() == "suspended" else "Active"
        try:
            numeric_id = int(record_id)
        except (ValueError, TypeError):
            numeric_id = record_id

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = (
                    self.client.table(table_name)
                    .update({"status": clean_status})
                    .eq("id", numeric_id)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return _strip_sensitive_fields(res.data[0])
            except Exception:
                pass

        for item in self._get_mock_data().setdefault(table_name, []):
            if str(item.get("id")) == str(record_id):
                item["status"] = clean_status
                return _strip_sensitive_fields(item)
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Look up an existing student, faculty, or admin account by email address."""
        clean_email = (email or "").strip().lower()
        if not clean_email:
            return None

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                std_res = self.client.table("students").select("*").eq("email", clean_email).execute()
                if std_res.data and len(std_res.data) > 0:
                    row = std_res.data[0]
                    if row.get("password_hash"):
                        self._password_hashes[clean_email] = row["password_hash"]
                    return {
                        "id": row.get("id"),
                        "fullName": row.get("name"),
                        "name": row.get("name"),
                        "email": row.get("email"),
                        "role": "student",
                        "course": row.get("course") or "Data Structures",
                        "status": row.get("status") or "Active",
                        "table": "students",
                        "createdAt": row.get("created_at")
                    }
            except Exception:
                pass

            try:
                fac_res = self.client.table("faculty").select("*").eq("email", clean_email).execute()
                if fac_res.data and len(fac_res.data) > 0:
                    row = fac_res.data[0]
                    if row.get("password_hash"):
                        self._password_hashes[clean_email] = row["password_hash"]
                    return {
                        "id": row.get("id"),
                        "fullName": row.get("full_name"),
                        "name": row.get("full_name"),
                        "email": row.get("email"),
                        "role": "faculty",
                        "department": row.get("department") or "Computer Science",
                        "status": row.get("status") or "Active",
                        "table": "faculty",
                        "createdAt": row.get("created_at")
                    }
            except Exception:
                pass

            try:
                adm_res = self.client.table("admins").select("*").eq("email", clean_email).execute()
                if adm_res.data and len(adm_res.data) > 0:
                    row = adm_res.data[0]
                    if row.get("password_hash"):
                        self._password_hashes[clean_email] = row["password_hash"]
                    return {
                        "id": row.get("id"),
                        "fullName": row.get("full_name"),
                        "name": row.get("full_name"),
                        "email": row.get("email"),
                        "role": "admin",
                        "status": row.get("status") or "Active",
                        "table": "admins",
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
                    "course": s.get("course") or "Data Structures",
                    "status": s.get("status") or "Active",
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
                    "department": f.get("department") or "Computer Science",
                    "status": f.get("status") or "Active",
                    "table": "faculty",
                    "createdAt": f.get("created_at")
                }
        for a in self._get_mock_data().get("admins", []):
            if str(a.get("email", "")).strip().lower() == clean_email:
                return {
                    "id": a.get("id"),
                    "fullName": a.get("full_name"),
                    "name": a.get("full_name"),
                    "email": a.get("email"),
                    "role": "admin",
                    "status": a.get("status") or "Active",
                    "table": "admins",
                    "createdAt": a.get("created_at")
                }
        return None

    def get_password_hash(self, email: str) -> Optional[str]:
        """Retrieves the stored password hash for an email if present."""
        clean_email = (email or "").strip().lower()
        if clean_email in self._password_hashes:
            return self._password_hashes[clean_email]
        # Populate cache from database if user exists
        self.get_user_by_email(clean_email)
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
        - Students are inserted into public.students (name, email, password_hash).
        - Faculty are inserted into public.faculty (full_name, email, department, password_hash).
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

        existing = self.get_user_by_email(clean_email)
        if existing is not None:
            raise DuplicateAccountError(f"An account with email '{clean_email}' is already registered.")

        if self._is_testing_mode():
            now_iso = datetime.now(timezone.utc).isoformat()
            if clean_role == "student":
                students_list = self._get_mock_data().setdefault("students", [])
                new_id = max([int(s.get("id", 0)) for s in students_list] + [0]) + 1
                record = {
                    "id": new_id,
                    "name": clean_name,
                    "email": clean_email,
                    "course": department or "Data Structures",
                    "status": "Active",
                    "created_at": now_iso
                }
                students_list.append(record)
                self._password_hashes[clean_email] = password_hash
                return {
                    "id": new_id,
                    "fullName": clean_name,
                    "name": clean_name,
                    "email": clean_email,
                    "role": "student",
                    "course": record["course"],
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
                    "status": "Active",
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
                    "department": record["department"],
                    "table": "faculty",
                    "createdAt": now_iso
                }

        if not self._ensure_connection() or not self.client:
            raise RuntimeError(
                "Database connection is unavailable. Account could not be saved to Supabase PostgreSQL."
            )

        try:
            if clean_role == "student":
                payload = {
                    "name": clean_name,
                    "email": clean_email,
                    "password_hash": password_hash
                }
                try:
                    res = self.client.table("students").insert(payload).execute()
                except Exception:
                    res = self.client.table("students").insert({"name": clean_name, "email": clean_email}).execute()
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
                    "course": inserted.get("course") or "Data Structures",
                    "table": "students",
                    "createdAt": inserted.get("created_at") or datetime.now(timezone.utc).isoformat()
                }
            else:
                payload = {
                    "full_name": clean_name,
                    "email": clean_email,
                    "department": department or "Computer Science",
                    "password_hash": password_hash
                }
                try:
                    res = self.client.table("faculty").insert(payload).execute()
                except Exception:
                    res = self.client.table("faculty").insert({
                        "full_name": clean_name,
                        "email": clean_email,
                        "department": department or "Computer Science"
                    }).execute()
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
                    "department": inserted.get("department") or department or "Computer Science",
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
    # Courses, Materials & Announcements (Course Hub)
    # ==========================================
    def get_courses(self) -> List[Dict[str, Any]]:
        """Fetch courses from public.courses."""
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("courses").select("*").order("id").execute()
                if res.data is not None:
                    return res.data
            except Exception:
                pass
        return self._get_mock_data().get("courses", [
            {"id": 1, "course_name": "Data Structures & Algorithms", "course_code": "CS-301"}
        ])

    def get_course_materials(self, course_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch study materials uploaded or linked by faculty."""
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                query = self.client.table("course_materials").select("*")
                if course_code:
                    query = query.eq("course_code", course_code)
                res = query.order("created_at", desc=True).execute()
                if res.data is not None:
                    return [
                        {
                            **m,
                            "resource_type": m.get("resource_type") or m.get("material_type") or "Lecture Notes",
                            "content_or_url": m.get("content_or_url") or m.get("description") or m.get("resource_url") or ""
                        }
                        for m in res.data
                    ]
            except Exception:
                pass
        materials = self._get_mock_data().get("course_materials", [])
        if course_code:
            materials = [m for m in materials if m.get("course_code") == course_code]
        return [
            {
                **m,
                "resource_type": m.get("resource_type") or m.get("material_type") or "Lecture Notes",
                "content_or_url": m.get("content_or_url") or m.get("description") or m.get("resource_url") or ""
            }
            for m in materials
        ]

    def create_course_material(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a new study material in Supabase."""
        mat_type = (data.get("material_type") or data.get("resource_type") or "Lecture Notes").strip()
        desc_or_url = (data.get("description") or data.get("content_or_url") or data.get("resource_url") or "").strip()
        payload = {
            "title": (data.get("title") or "").strip(),
            "topic": (data.get("topic") or "General").strip(),
            "material_type": mat_type,
            "resource_url": (data.get("resource_url") or "").strip() or None,
            "description": desc_or_url or None,
            "course_code": (data.get("course_code") or "CS-301").strip(),
            "uploaded_by": (data.get("uploaded_by") or "Faculty").strip()
        }
        if not payload["title"]:
            raise ValueError("Study material 'title' is required.")

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            res = self.client.table("course_materials").insert(payload).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                return {
                    **row,
                    "resource_type": row.get("material_type") or mat_type,
                    "content_or_url": row.get("description") or row.get("resource_url") or desc_or_url
                }

        items = self._get_mock_data().setdefault("course_materials", [])
        new_id = max([int(i.get("id", 0)) for i in items] + [0]) + 1
        record = {
            "id": new_id,
            **payload,
            "resource_type": mat_type,
            "content_or_url": desc_or_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        items.insert(0, record)
        return record

    def get_announcements(self, course_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch course announcements published by faculty."""
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                query = self.client.table("announcements").select("*")
                if course_code:
                    query = query.eq("course_code", course_code)
                res = query.order("created_at", desc=True).execute()
                if res.data is not None:
                    return [
                        {
                            **a,
                            "message": a.get("message") or a.get("content") or "",
                            "published_by": a.get("published_by") or a.get("author_name") or "Faculty"
                        }
                        for a in res.data
                    ]
            except Exception:
                pass
        announcements = self._get_mock_data().get("announcements", [])
        if course_code:
            announcements = [a for a in announcements if a.get("course_code") == course_code]
        return [
            {
                **a,
                "message": a.get("message") or a.get("content") or "",
                "published_by": a.get("published_by") or a.get("author_name") or "Faculty"
            }
            for a in announcements
        ]

    def create_announcement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Publish and persist a new course announcement in Supabase."""
        content_text = (data.get("content") or data.get("message") or "").strip()
        author_text = (data.get("author_name") or data.get("published_by") or "Faculty").strip()
        payload = {
            "title": (data.get("title") or "").strip(),
            "content": content_text,
            "course_code": (data.get("course_code") or "CS-301").strip(),
            "author_name": author_text,
            "priority": (data.get("priority") or "normal").strip()
        }
        if not payload["title"] or not payload["content"]:
            raise ValueError("Announcement 'title' and 'content' (or 'message') are required.")

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            res = self.client.table("announcements").insert(payload).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                return {
                    **row,
                    "message": row.get("content") or content_text,
                    "published_by": row.get("author_name") or author_text
                }

        items = self._get_mock_data().setdefault("announcements", [])
        new_id = max([int(i.get("id", 0)) for i in items] + [0]) + 1
        record = {
            "id": new_id,
            **payload,
            "message": content_text,
            "published_by": author_text,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        items.insert(0, record)
        return record

    # ==========================================
    # Faculty–Student Collaboration & Interventions
    # ==========================================
    def get_interventions(
        self,
        student_id: Optional[Any] = None,
        course_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch faculty feedback, targeted practice notices, and 1-to-1 intervention requests."""
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                query = self.client.table("interventions").select("*")
                if student_id is not None:
                    query = query.eq("student_id", int(student_id))
                if course_code:
                    query = query.eq("course_code", course_code)
                res = query.order("created_at", desc=True).execute()
                if res.data is not None:
                    return [
                        {
                            **i,
                            "details": i.get("details") or i.get("message") or ""
                        }
                        for i in res.data
                    ]
            except Exception:
                pass

        items = self._get_mock_data().get("interventions", [])
        if student_id is not None:
            items = [i for i in items if str(i.get("student_id")) == str(student_id)]
        if course_code:
            items = [i for i in items if i.get("course_code") == course_code]
        return [
            {
                **i,
                "details": i.get("details") or i.get("message") or ""
            }
            for i in items
        ]

    def create_intervention(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a collaboration record in public.interventions:
        - Faculty feedback / targeted practice assignment ('faculty_feedback', 'targeted_practice')
        - Student 1-to-1 help request / office-hours booking ('help_request', 'office_hours')
        """
        student_id = data.get("student_id")
        if student_id is None:
            raise ValueError("'student_id' is required.")

        student = self.get_student_by_id(student_id)
        if not student:
            raise ValueError(f"Student ID '{student_id}' not found.")

        msg_text = (data.get("message") or data.get("details") or "").strip()
        payload = {
            "student_id": int(student["id"]),
            "student_name": (data.get("student_name") or student.get("name") or "Student").strip(),
            "faculty_name": (data.get("faculty_name") or "Course Faculty").strip(),
            "course_code": (data.get("course_code") or "CS-301").strip(),
            "topic": (data.get("topic") or "General").strip(),
            "intervention_type": (data.get("intervention_type") or "faculty_feedback").strip(),
            "initiated_by": (data.get("initiated_by") or "faculty").strip(),
            "title": (data.get("title") or "Academic Support").strip(),
            "message": msg_text,
            "faculty_response": (data.get("faculty_response") or "").strip() or None,
            "preferred_slot": (data.get("preferred_slot") or "").strip() or None,
            "status": (data.get("status") or "open").strip()
        }
        if not payload["message"]:
            raise ValueError("Intervention or feedback 'message' is required.")

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            res = self.client.table("interventions").insert(payload).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                return {**row, "details": row.get("message") or msg_text}

        items = self._get_mock_data().setdefault("interventions", [])
        new_id = max([int(i.get("id", 0)) for i in items] + [0]) + 1
        now_iso = datetime.now(timezone.utc).isoformat()
        record = {
            "id": new_id,
            **payload,
            "details": msg_text,
            "created_at": now_iso,
            "updated_at": now_iso
        }
        items.insert(0, record)
        return record

    def update_intervention(self, intervention_id: Any, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates an intervention record (e.g., faculty response and office-hours status)."""
        try:
            numeric_id = int(intervention_id)
        except (ValueError, TypeError):
            numeric_id = intervention_id

        patch: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if "faculty_response" in updates and updates["faculty_response"] is not None:
            patch["faculty_response"] = str(updates["faculty_response"]).strip()
        if "status" in updates and updates["status"]:
            patch["status"] = str(updates["status"]).strip()
        if "preferred_slot" in updates and updates["preferred_slot"] is not None:
            patch["preferred_slot"] = str(updates["preferred_slot"]).strip()
        if "faculty_name" in updates and updates["faculty_name"]:
            patch["faculty_name"] = str(updates["faculty_name"]).strip()

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = (
                    self.client.table("interventions")
                    .update(patch)
                    .eq("id", numeric_id)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        for item in self._get_mock_data().setdefault("interventions", []):
            if str(item.get("id")) == str(intervention_id):
                item.update(patch)
                return item
        return None

    # ==========================================
    # Activities & Assignments API
    # ==========================================
    def get_activities(self, student_id: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Fetch course activities. If student_id is provided, returns course-wide activities
        plus any targeted remedial activities assigned specifically to that student.
        """
        all_acts: List[Dict[str, Any]] = []
        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("activities").select("*").order("id").execute()
                if res.data is not None:
                    all_acts = res.data
            except Exception:
                all_acts = self._get_mock_data().get("activities", [])
        else:
            all_acts = self._get_mock_data().get("activities", [])

        if student_id is not None:
            return [
                a for a in all_acts
                if a.get("assigned_student_id") is None
                or str(a.get("assigned_student_id")) == str(student_id)
            ]
        return all_acts

    def get_activity_by_id(self, activity_id: Any) -> Optional[Dict[str, Any]]:
        """Fetch single activity by ID."""
        try:
            numeric_id = int(activity_id)
        except (ValueError, TypeError):
            numeric_id = activity_id

        if self._ensure_connection() and self.client and not self._is_testing_mode():
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
        """Create a new course activity or targeted student exercise in Supabase."""
        base_payload = {
            "title": activity_data["title"],
            "topic": activity_data["topic"],
            "activity_type": activity_data.get("activity_type", "Quiz"),
            "max_score": float(activity_data.get("max_score", 100))
        }
        extended_payload = {
            **base_payload,
            "instructions": (activity_data.get("instructions") or "").strip() or None,
            "due_date": (activity_data.get("due_date") or "").strip() or None,
            "assigned_student_id": int(activity_data["assigned_student_id"]) if activity_data.get("assigned_student_id") else None,
            "course_code": (activity_data.get("course_code") or "CS-301").strip(),
            "created_by_faculty": (activity_data.get("created_by_faculty") or "").strip() or None
        }

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("activities").insert(extended_payload).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                try:
                    res = self.client.table("activities").insert(base_payload).execute()
                    if res.data and len(res.data) > 0:
                        return res.data[0]
                except Exception:
                    pass

        activities_list = self._get_mock_data().setdefault("activities", [])
        mock_id = max([int(a.get("id", 0)) for a in activities_list] + [0]) + 1
        new_record = {
            "id": mock_id,
            **extended_payload,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        activities_list.append(new_record)
        return new_record

    # ==========================================
    # Submissions & Evaluation Queue API
    # ==========================================
    def get_submissions(self, student_id: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Fetch submissions joined with activity and student details."""
        students_map = {str(s.get("id")): s.get("name", f"Student #{s.get('id')}") for s in self.get_students()}

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                query = self.client.table("submissions").select("*, activities(*)")
                if student_id is not None:
                    try:
                        numeric_id = int(student_id)
                    except (ValueError, TypeError):
                        numeric_id = student_id
                    query = query.eq("student_id", numeric_id)
                res = query.order("submitted_at", desc=True).execute()

                submissions = []
                for sub in res.data or []:
                    act = sub.get("activities") or {}
                    sid = sub.get("student_id")
                    submissions.append({
                        "id": sub.get("id"),
                        "student_id": sid,
                        "student_name": students_map.get(str(sid), f"Student #{sid}"),
                        "activity_id": sub.get("activity_id"),
                        "score": float(sub.get("score", 0)),
                        "status": sub.get("status", "submitted"),
                        "is_late": sub.get("status") == "late",
                        "response_text": sub.get("response_text"),
                        "feedback": sub.get("feedback"),
                        "evaluated_by": sub.get("evaluated_by"),
                        "evaluated_at": sub.get("evaluated_at"),
                        "submitted_at": sub.get("submitted_at"),
                        "activity_title": act.get("title", f"Activity {sub.get('activity_id')}"),
                        "activity_type": act.get("activity_type", "Assignment"),
                        "topic": act.get("topic", "General"),
                        "max_score": float(act.get("max_score", 100))
                    })
                return submissions
            except Exception:
                pass

        raw_submissions = self._get_mock_data().get("submissions", [])
        activities_map = {a["id"]: a for a in self._get_mock_data().get("activities", [])}

        normalized = []
        for sub in raw_submissions:
            if student_id is not None and str(sub.get("student_id")) != str(student_id):
                continue
            act = activities_map.get(sub.get("activity_id"), {})
            sid = sub.get("student_id")
            normalized.append({
                "id": sub.get("id"),
                "student_id": sid,
                "student_name": students_map.get(str(sid), f"Student #{sid}"),
                "activity_id": sub.get("activity_id"),
                "score": float(sub.get("score", 0)),
                "status": sub.get("status", "submitted"),
                "is_late": sub.get("status") == "late",
                "response_text": sub.get("response_text"),
                "feedback": sub.get("feedback"),
                "evaluated_by": sub.get("evaluated_by"),
                "evaluated_at": sub.get("evaluated_at"),
                "submitted_at": sub.get("submitted_at"),
                "activity_title": act.get("title", f"Activity {sub.get('activity_id')}"),
                "activity_type": act.get("activity_type", "Assignment"),
                "topic": act.get("topic", "General"),
                "max_score": float(act.get("max_score", 100))
            })
        return normalized

    def create_submission(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a student submission (score or assignment response) in Supabase."""
        status = "late" if submission_data.get("is_late") else submission_data.get("status", "submitted")

        base_payload = {
            "student_id": int(submission_data["student_id"]),
            "activity_id": int(submission_data["activity_id"]),
            "score": float(submission_data.get("score", 0)),
            "status": status
        }
        extended_payload = {
            **base_payload,
            "response_text": (submission_data.get("response_text") or "").strip() or None,
            "feedback": (submission_data.get("feedback") or "").strip() or None
        }

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = self.client.table("submissions").insert(extended_payload).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                try:
                    res = self.client.table("submissions").insert(base_payload).execute()
                    if res.data and len(res.data) > 0:
                        return res.data[0]
                except Exception:
                    pass

        subs_list = self._get_mock_data().setdefault("submissions", [])
        mock_id = max([int(s.get("id", 0)) for s in subs_list] + [0]) + 1
        new_record = {
            "id": mock_id,
            **extended_payload,
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        subs_list.append(new_record)
        return new_record

    def evaluate_submission(
        self,
        submission_id: Any,
        score: float,
        feedback: str,
        evaluated_by: str = "Faculty"
    ) -> Optional[Dict[str, Any]]:
        """Allows faculty to evaluate a student submission with marks and written feedback."""
        try:
            numeric_id = int(submission_id)
        except (ValueError, TypeError):
            numeric_id = submission_id

        numeric_score = float(score)
        if numeric_score < 0 or numeric_score > 100:
            raise ValueError("Score must be between 0 and 100.")

        patch = {
            "score": numeric_score,
            "feedback": (feedback or "").strip(),
            "evaluated_by": (evaluated_by or "Faculty").strip(),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "status": "evaluated"
        }

        if self._ensure_connection() and self.client and not self._is_testing_mode():
            try:
                res = (
                    self.client.table("submissions")
                    .update(patch)
                    .eq("id", numeric_id)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        for sub in self._get_mock_data().setdefault("submissions", []):
            if str(sub.get("id")) == str(submission_id):
                sub.update(patch)
                return sub
        return None


# Singleton instance
db_service = DatabaseService()
