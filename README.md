# EduNexus AI

> **Tagline:** "From academic activity to actionable growth."

EduNexus AI is a modern academic intelligence platform built for university courses (currently demonstrating **Data Structures**). It bridges daily student learning activities with actionable growth insights for students, faculty, and administrators.

---

## Architecture Overview

```
                               ┌────────────────────────────────┐
                               │   Frontend (Vanilla JS/HTML/CSS)│
                               │  - Student Dashboard           │
                               │  - Faculty Cohort Analytics    │
                               │  - Admin Control Panel         │
                               │  - Auth (Login & Register)     │
                               └───────────────┬────────────────┘
                                               │ HTTP / REST JSON
                                               ▼
                               ┌────────────────────────────────┐
                               │      Flask REST API (Python)   │
                               │  - /health                     │
                               │  - /api/students               │
                               │  - /api/activities             │
                               │  - /api/student/<id>/dashboard │
                               │  - /api/faculty/overview       │
                               │  - /api/submissions           │
                               │  - /api/analyze                │
                               └───────────────┬────────────────┘
                                               │ Supabase SDK
                        ┌──────────────────────┴──────────────────────┐
                        ▼                                             ▼
        ┌───────────────────────────────┐             ┌───────────────────────────────┐
        │     Supabase PostgreSQL       │             │    Local Synthetic Fallback   │
        │  - public.students            │             │  - mock_data.json             │
        │  - public.activities          │             │  (activates when offline/keys │
        │  - public.submissions         │             │   are not configured)         │
        └───────────────────────────────┘             └───────────────────────────────┘
```

- **Frontend:** Responsive HTML5, Vanilla JavaScript, and external CSS without inline styles or script tags.
- **Backend:** Python Flask 3.1 REST API with CORS support.
- **Database:** Supabase PostgreSQL with Row Level Security (RLS) policies.
- **Analytics Engine:** Explainable, deterministic Python rule engine for weak-topic detection and evidence-based recommendations.
- **Fallback Resilience:** Automatic in-memory fallback to `mock_data.json` if network access or Supabase credentials are unavailable.

---

## Academic Domain & Business Logic

- **Course:** Data Structures
- **Curricular Topics:** `Arrays`, `Linked Lists`, `Stacks`, `Queues`, `Recursion`
- **Fictional Cohort:** `Aanya Patel`, `Rohan Shah`, `Meera Joshi`, `Arjun Desai`

### Weak-Topic Detection Rule
A topic is flagged as weak when:
1. The student's average score across activities for that topic is **below 50%**, OR
2. **Two or more recent activities** for that topic have scores **below 50%**.

*Late submission evidence:* A late submission is documented as supporting evidence in the diagnostic explanation, but does not independently flag a topic as weak.

### Evidence-Based Recommendations Contract
Every generated recommendation adheres strictly to the 6-field contract:
1. `topic` — Curricular topic (e.g. Arrays)
2. `score` — Student's computed topic mastery percentage
3. `evidence` — Explainable reason citing scores and assessment titles
4. `recommended_action` — Concrete study task or remedial practice
5. `resource` — High-impact pedagogical resource or visualizer module
6. `priority` — `"High"`, `"Medium"`, or `"Low"`

---

## Getting Started Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Git

### 1. Clone & Navigate to Project
```bash
git clone <repo-url>
cd "EduNexus ai"
```

### 2. Set Up Virtual Environment
```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate your Supabase credentials in `.env`:
```env
FLASK_ENV=development
FLASK_DEBUG=1
PORT=5000

SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
```
*(If `.env` is omitted or credentials are invalid, the backend automatically operates in synthetic fallback mode using `mock_data.json` without crashing).*

### 5. Run the Flask Server
```bash
python app.py
```
Open your browser at `http://localhost:5000` to interact with the platform.

---

## Running Automated Tests

The project includes unit and integration tests covering analytics rules, recommendation generation, API contracts, database fallbacks, and validation errors.

```bash
# Run full pytest suite with verbose output
pytest tests/ -v
```

Expected output:
```
======================= 36 passed in 14.56s =======================
```

---

## Database Setup (Supabase PostgreSQL)

If provisioning a fresh Supabase project:
1. Open your Supabase SQL Editor at [supabase.com](https://supabase.com).
2. Execute the provided [`schema.sql`](file:///schema.sql) file.
3. The script creates:
   - `students` table
   - `activities` table with `topic` constraint
   - `submissions` table with foreign keys and cascade rules
   - Row Level Security (RLS) policies allowing public read access for demo accounts
   - Seed data for the 4 students, 6 activities, and initial submissions.

---

## Deployment to Render

This application is ready for deployment on [Render](https://render.com).

### Step-by-Step Render Setup:
1. Push your repository to GitHub.
2. Log into the Render Dashboard and click **New +** → **Web Service**.
3. Select your GitHub repository.
4. Configure the build and runtime settings:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Under **Environment Variables**, add:
   - `SUPABASE_URL`: Your live Supabase URL
   - `SUPABASE_KEY`: Your live Supabase API key
   - `FLASK_DEBUG`: `0`
6. Click **Deploy Web Service**. Render will provision the container and provide your live URL (e.g., `https://edunexus-ai.onrender.com`).

---

## API Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health probe & Supabase connection status |
| `GET` | `/api/students` | List all enrolled students |
| `GET` | `/api/activities` | List all course activities & modules |
| `POST` | `/api/activities` | Create a new activity (`Arrays`, `Linked Lists`, `Stacks`, `Queues`, `Recursion`) |
| `GET` | `/api/student/<id>/dashboard` | Student analytics, mastery scores, weak topics & recommendations |
| `GET` | `/api/faculty/overview` | Class average, cohort topic breakdown & at-risk student intervention alerts |
| `POST` | `/api/submissions` | Record student activity score |
| `POST` | `/api/analyze` | On-demand academic diagnostic analytics |
| `POST` | `/auth/login` | User login endpoint |
| `POST` | `/auth/register` | Student/faculty registration endpoint (admin blocked) |
