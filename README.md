# SkillSense AI

SkillSense AI is a full-stack platform for student skill verification, repository review, interview readiness, and recruiter/university operations. It uses a React + Vite frontend and a Django REST backend.

## Highlights

- Resume-driven student onboarding with profile extraction.
- Skill scoring across coding, communication, authenticity, and placement readiness.
- Deep GitHub repository review with file-level findings, commit signals, and optional AI coaching.
- AI interview simulator with feedback, metrics, and session history.
- Recruiter workflows for job briefs, candidate pipeline, saved searches, and interview scheduling.
- University workflows for analytics, interventions, batch uploads, and placement drives.

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS

### Backend

- Django
- Django REST Framework
- SimpleJWT
- SQLite by default, `DATABASE_URL` support for production databases

## Project Structure

- `src/` - React frontend
- `skillsence/` - Django settings and project entrypoints
- `accounts/` - authentication, profile, and scoring APIs
- `skills/` - repository analysis, interviews, dashboards, reports, and workflow APIs
- `content/` - public landing-page content blocks

## Local Setup

### Backend

```sh
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend default: `http://127.0.0.1:8000`

### Frontend

```sh
npm install
npm run dev
```

Frontend default: `http://127.0.0.1:5173`

## Environment Variables

Use `.env.example` as the starting point.

### Core Django

- `DJANGO_DEBUG`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`

### Production Security

- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SESSION_COOKIE_SECURE`
- `DJANGO_CSRF_COOKIE_SECURE`
- `DJANGO_SECURE_HSTS_SECONDS`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `DJANGO_SECURE_HSTS_PRELOAD`
- `DJANGO_USE_X_FORWARDED_HOST`
- `DJANGO_SECURE_PROXY_SSL_HEADER`

### AI / Git Analysis

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_API_BASE`
- `GITHUB_TOKEN`
- `AI_REPO_CACHE_ENABLED`
- `AI_REPO_CACHE_CHARS`
- `AI_REPO_CHUNK_CHARS`
- `AI_REPO_MAX_FILES`
- `AI_REPO_PREVIEW_CHARS`

### Frontend

- `VITE_API_BASE_URL`

## Main API Endpoints

- `POST /api/accounts/signup/`
- `POST /api/accounts/login/`
- `GET /api/accounts/profile/`
- `PATCH /api/accounts/profile/`
- `GET /api/skills/dashboard/`
- `GET /api/skills/code-analysis/`
- `POST /api/skills/code-analysis/`
- `GET /api/skills/code-analysis/<report_id>/file/?path=...`
- `GET /api/skills/ai-interview/`
- `POST /api/skills/ai-interview/action/`
- `GET /api/skills/skill-passport/pdf/`

## Deployment

### 1. Build frontend

```sh
npm install
npm run build
```

### 2. Install backend dependencies

```sh
pip install -r requirements.txt
```

### 3. Configure environment

Minimum production variables:

```sh
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

Optional but recommended:

```sh
OPENAI_API_KEY=...
GITHUB_TOKEN=...
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
DJANGO_SECURE_HSTS_SECONDS=31536000
```

### 4. Prepare database and static files

```sh
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. Run the app

```sh
gunicorn skillsence.wsgi:application --bind 0.0.0.0:8000
```

Or use the included `Procfile` on supported platforms.

## Notes

- Without `OPENAI_API_KEY`, repository analysis still runs using heuristics, but AI coaching sections stay empty.
- Runtime artifacts such as `db.sqlite3`, `media/`, and `__pycache__/` are intentionally ignored in Git.
