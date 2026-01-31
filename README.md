# Skillsence AI (SkillSense-AI)

Skillsence AI is a full‑stack platform for student skill verification and interview readiness. It combines a React + Vite frontend with a Django REST backend to analyze profiles, score skills, and run AI‑assisted interviews.

## Highlights

- Resume‑driven onboarding that auto‑fills profile details.
- Skill scoring across coding, communication, authenticity, and placement readiness.
- AI interview simulator with adaptive follow‑ups and feedback.
- Platform insights for students, recruiters, and universities.
- Skill passport PDF reports and performance trends.

## Tech Stack

Frontend:
- React + TypeScript (Vite)
- Tailwind CSS + shadcn‑ui

Backend:
- Django + Django REST Framework
- SimpleJWT for auth
- SQLite (default local)

## Features

- **Student registration** with resume parsing (PDF/DOCX/TXT).
- **AI interview** sessions with real‑time feedback, metrics, and tips.
- **Skill scoring** based on linked platforms and interview responses.
- **Dashboards** for students, recruiters, and universities.
- **Reports**: skill passport PDF + score summaries.

## Project Structure

- `src/` – React frontend
- `skillsence/` – Django project settings
- `accounts/` – auth + profile APIs
- `skills/` – scoring, interview, skill passport, media endpoints
- `templates/`, `static/`, `staticfiles/` – Django assets

## Getting Started (Local)

### Backend (Django)

```sh
# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Run backend
python manage.py runserver
```

Backend runs at `http://127.0.0.1:8000`.

### Frontend (Vite)

```sh
# Install dependencies
npm install

# Start frontend
npm run dev
```

Frontend runs at `http://127.0.0.1:5173` (default Vite port).

## Environment Variables

Create a `.env.local` (frontend) or set env vars in your shell for the backend.

Backend (Django):
- `OPENAI_API_KEY` – enables AI question generation and follow‑ups.
- `OPENAI_MODEL` – default: `gpt-4o-mini`.
- `OPENAI_API_BASE` – optional, default `https://api.openai.com/v1`.
- `GITHUB_TOKEN` – optional for GitHub analysis.
- `AI_REPO_CACHE_ENABLED` – default `true`.
- `AI_REPO_CACHE_CHARS` – repo snapshot limit, default `20000`.
- `AI_REPO_CHUNK_CHARS` – chunk size for code analysis, default `6000`.

## Key API Endpoints

- `POST /api/accounts/signup/` – register user
- `POST /api/accounts/login/` – login
- `GET /api/accounts/profile/` – profile
- `PATCH /api/accounts/profile/` – update profile
- `GET /api/skills/ai-interview/` – interview session state
- `POST /api/skills/ai-interview/action/` – start/respond/finish interview
- `GET /api/skills/skill-passport/pdf/` – PDF export

## AI Interview Flow

- AI asks intro questions first, then technical questions.
- Follow‑ups adapt to your last response (if `OPENAI_API_KEY` is set).
- Metrics and feedback update after each answer.
- End‑of‑interview summary highlights strengths and improvements.

## Deployment

Deploy frontend with any static host (Vercel, Netlify, etc.) and backend with a Django‑friendly host (Render, Railway, EC2, etc.). Configure environment variables on the backend host.

## License

Add your license here.
