# SkillSense AI

SkillSense AI is a full-stack placement-readiness and skill-verification platform for students, recruiters, and universities.

It combines resume parsing, GitHub-based engineering analysis, adaptive AI interviews, skill verification, recruiter workflow tooling, and university placement analytics in one product.

## What This Project Includes

### Student Features

- Resume-based onboarding and profile extraction
- JWT authentication and profile management
- Skill scoring across:
  - coding skill index
  - communication score
  - authenticity score
  - placement readiness
- Skill passport with downloadable PDF
- Resume builder with downloadable PDF
- Deep GitHub repository analysis with:
  - repo-level engineering score
  - file-level review summaries
  - architecture detection
  - commit and repository signal analysis
  - AI-generated review and coaching when an LLM key is configured
- Advanced AI interview lab with:
  - configurable target role
  - configurable seniority
  - configurable interview mode
  - adaptive follow-up questions
  - rubric-based scoring for communication, depth, ownership, evidence, tradeoffs, and confidence
  - session summary, recommendation, readiness score, and history
- Student progress dashboard
- Roadmap and recommendation surfaces
- Media/document upload support
- Notifications and verification workflow tracking

### Recruiter Features

- Recruiter login and approval-gated access flow
- Candidate discovery dashboard
- Candidate filtering and ranking
- Job brief creation
- JD-to-candidate matching
- Saved searches
- Candidate pipeline states
- Candidate report download
- Candidate resume download
- Interview scheduling

### University Features

- University login and approval-gated access flow
- University analytics dashboard
- Cohort filtering by branch, course, and year
- Readiness and score distribution views
- Intervention tracking
- CSV batch upload
- Placement drive creation and tracking
- Export-ready reporting surfaces

### Platform / Admin Features

- Django admin support for key operational models
- Approval workflows for recruiter and university onboarding
- Role-based access control across student, recruiter, and university users
- Environment-driven deployment configuration
- OpenAI-compatible LLM support through `OPENAI_API_BASE`
  - OpenAI
  - Groq
  - other OpenAI-compatible providers

## Tech Stack

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- TanStack Query
- Recharts
- Radix UI primitives

### Backend

- Django 4.2
- Django REST Framework
- Simple JWT
- Django CORS Headers
- ReportLab
- Matplotlib
- pdfminer / PyPDF2 / python-docx for document parsing

### Storage / Runtime

- SQLite by default for local development
- `DATABASE_URL` support for PostgreSQL and other production databases

## Architecture

- `src/` contains the React frontend
- `skillsence/` contains Django settings, project URLs, and deployment configuration
- `accounts/` contains authentication, profile, onboarding, and score APIs
- `skills/` contains the product domain:
  - interviews
  - repository analysis
  - recruiter workflows
  - university workflows
  - reports
  - notifications
- `content/` contains public landing page content blocks
- `templates/` and `dist/` are used when Django serves the built frontend

## Main Application Routes

### Public / Auth

- `/`
- `/student/start`
- `/student`
- `/student/register`
- `/recruiter`
- `/recruiter/register`
- `/university`
- `/university/register`

### Student

- `/dashboard`
- `/dashboard/code`
- `/dashboard/media`
- `/dashboard/passport`
- `/dashboard/interview`
- `/dashboard/progress`
- `/dashboard/roadmap`
- `/dashboard/resume-builder`
- `/dashboard/settings`

### Recruiter

- `/recruiter/dashboard`

### University

- `/university/dashboard`

## API Overview

### Accounts

- `POST /api/accounts/signup/`
- `POST /api/accounts/login/`
- `POST /api/accounts/logout/`
- `GET /api/accounts/profile/`
- `PATCH /api/accounts/profile/`
- `GET /api/accounts/dashboard/`
- `POST /api/accounts/recalculate/`
- `GET /api/accounts/score-report/`

### Skills / Student

- `GET /api/skills/dashboard/`
- `GET /api/skills/activities/`
- `GET /api/skills/verification-steps/`
- `GET /api/skills/recommendations/`
- `GET /api/skills/skill-suggestions/`
- `GET /api/skills/skill-passport/`
- `GET /api/skills/skill-passport/pdf/`
- `GET /api/skills/resume/`
- `GET /api/skills/resume-builder/`
- `GET /api/skills/resume-builder/pdf/`
- `GET /api/skills/notifications/`
- `POST /api/skills/notifications/<id>/read/`
- `GET /api/skills/ai-interview/`
- `POST /api/skills/ai-interview/action/`
- `POST /api/skills/code-analysis/`
- `GET /api/skills/code-analysis/<report_id>/file/?path=...`
- `GET /api/skills/media/`
- `GET /api/skills/progress/`
- `GET /api/skills/roadmap/`
- `GET /api/skills/settings/`
- `GET /api/skills/performance/`

### Recruiter

- `GET /api/skills/recruiter-dashboard/`
- `GET /api/skills/recruiter-dashboard/jobs/`
- `POST /api/skills/recruiter-dashboard/jobs/`
- `GET /api/skills/recruiter-dashboard/pipeline/<candidate_id>/`
- `POST /api/skills/recruiter-dashboard/pipeline/<candidate_id>/`
- `GET /api/skills/recruiter-dashboard/saved-searches/`
- `POST /api/skills/recruiter-dashboard/saved-searches/`
- `GET /api/skills/recruiter-dashboard/report/<student_id>/`
- `GET /api/skills/recruiter-dashboard/resume/<student_id>/`
- `GET /api/skills/interview-schedules/`
- `POST /api/skills/interview-schedules/`

### University

- `GET /api/skills/university-dashboard/`
- `POST /api/skills/university-dashboard/batch-upload/`
- `GET /api/skills/university-dashboard/interventions/<student_id>/`
- `POST /api/skills/university-dashboard/interventions/<student_id>/`
- `GET /api/skills/university-dashboard/drives/`
- `POST /api/skills/university-dashboard/drives/`

## Local Development

### Prerequisites

- Python
- Node.js
- npm

Windows examples below use PowerShell.

### 1. Clone and install

```powershell
git clone <your-repo-url>
cd aura-skills-main
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
```

### 2. Configure environment

Copy `.env.example` into `.env.local` and adjust values as needed.

```powershell
Copy-Item .env.example .env.local
```

At minimum for local development:

```env
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=dev-only-secret-key
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If you want GitHub + AI-powered analysis:

```env
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_provider_key
OPENAI_API_BASE=https://api.openai.com/v1/chat/completions
OPENAI_MODEL=gpt-4o-mini
```

If you are using Groq:

```env
OPENAI_API_KEY=your_groq_key
OPENAI_API_BASE=https://api.groq.com/openai/v1/chat/completions
OPENAI_MODEL=llama-3.3-70b-versatile
```

### 3. Apply migrations

```powershell
python manage.py migrate
```

### 4. Run the backend

```powershell
python manage.py runserver
```

Backend default:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 5. Run the frontend in Vite dev mode

```powershell
npm run dev
```

Frontend default:

- [http://127.0.0.1:5173](http://127.0.0.1:5173)

## Single-Server Local Run

If you want Django to serve the built frontend:

```powershell
npm run build
python manage.py runserver
```

Then open:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Environment Variables

### Core Django

- `DJANGO_DEBUG`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOW_ALL`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `DJANGO_DB_CONN_MAX_AGE`

### Security / Proxy

- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SESSION_COOKIE_SECURE`
- `DJANGO_CSRF_COOKIE_SECURE`
- `DJANGO_SECURE_HSTS_SECONDS`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `DJANGO_SECURE_HSTS_PRELOAD`
- `DJANGO_SECURE_CONTENT_TYPE_NOSNIFF`
- `DJANGO_USE_X_FORWARDED_HOST`
- `DJANGO_SECURE_PROXY_SSL_HEADER`
- `DJANGO_SESSION_COOKIE_SAMESITE`
- `DJANGO_CSRF_COOKIE_SAMESITE`
- `DJANGO_X_FRAME_OPTIONS`

### AI / GitHub / Repo Review

- `GITHUB_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `OPENAI_MODEL`
- `AI_REPO_CACHE_ENABLED`
- `AI_REPO_CACHE_CHARS`
- `AI_REPO_CHUNK_CHARS`
- `AI_REPO_MAX_FILES`
- `AI_REPO_PREVIEW_CHARS`

### Frontend

- `VITE_API_BASE_URL`

## Testing and Validation

### Backend

```powershell
python manage.py check
python manage.py test
```

### Frontend

```powershell
npm run build
```

### Lint

```powershell
npm run lint
```

Note: the build currently passes. If lint fails, that is frontend lint debt rather than a build blocker.

## Deployment

### Production Checklist

- Set `DJANGO_DEBUG=false`
- Set a real `DJANGO_SECRET_KEY`
- Set `DJANGO_ALLOWED_HOSTS`
- Set `DJANGO_CORS_ALLOWED_ORIGINS`
- Set `DJANGO_CSRF_TRUSTED_ORIGINS`
- Set `DATABASE_URL`
- Set HTTPS-related security env vars
- Run migrations
- Collect static files
- Configure media persistence
- Configure your LLM provider and GitHub token if AI features are required

### Recommended Production Variables

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true
DJANGO_SECURE_HSTS_PRELOAD=true
```

### Build and deploy

```powershell
npm install
npm run build
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn skillsence.wsgi:application --bind 0.0.0.0:8000
```

This repository also includes:

- `Procfile` for platforms that support Procfile-based startup

Current `Procfile` process:

```text
web: python manage.py collectstatic --noinput && gunicorn skillsence.wsgi:application --bind 0.0.0.0:$PORT
```

## Notes

- Repository analysis still works without `OPENAI_API_KEY`, but the AI-written coaching sections fall back to heuristics only.
- `OPENAI_API_BASE` makes the project provider-agnostic for OpenAI-compatible endpoints.
- Local runtime artifacts such as `db.sqlite3`, `media/`, logs, and `__pycache__/` should not be committed.

## Repository Structure

```text
accounts/        auth, onboarding, profile, score APIs
content/         landing page content blocks
skills/          interviews, repo analysis, dashboards, reports, notifications
skillsence/      Django settings, project URLs, WSGI
src/             React frontend
templates/       Django template shell
dist/            built frontend output
manage.py        Django entrypoint
Procfile         production process command
```

## Summary

SkillSense AI is not just a student dashboard. It is a multi-role placement intelligence system with:

- student verification
- engineering analysis
- adaptive interview simulation
- recruiter workflow tooling
- university placement analytics

If you are extending the product, the highest-impact surfaces are:

- deeper recruiter matching
- stronger university reporting
- more evidence-backed student verification
- production deployment hardening
