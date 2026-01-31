from datetime import timedelta
import io
import math
import json
import os
import base64
import urllib.request
import urllib.error
from urllib.parse import urlparse
import random
from django.db.models import Avg, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.http import HttpResponse

from .models import (
    Skill,
    Activity,
    ScoreCard,
    VerificationStep,
    ScoreSnapshot,
    AIInterviewSession,
    CodeAnalysisReport,
    MediaUpload,
    RepoFileSnapshot,
)
from .serializers import (
    SkillSerializer,
    ActivitySerializer,
    ScoreCardSerializer,
    VerificationStepSerializer,
)
from accounts.models import User
from accounts.scoring import calculate_student_scores, score_breakdown, upsert_scorecards
from content.models import ContentBlock

def _bool(value):
    return bool(value and str(value).strip())


def _require_role(user, role):
    return user and getattr(user, "role", None) == role


def _repo_cache_enabled():
    return os.environ.get("AI_REPO_CACHE_ENABLED", "true").strip().lower() in {"1", "true", "yes"}


def _repo_cache_max_chars():
    try:
        return int(os.environ.get("AI_REPO_CACHE_CHARS", "20000"))
    except (TypeError, ValueError):
        return 20000


def _store_repo_file_snapshot(user, repo_url, path, sha, content, size, lines):
    if not user or not _repo_cache_enabled():
        return
    max_chars = _repo_cache_max_chars()
    stored_content = content if max_chars <= 0 else (content or "")[:max_chars]
    RepoFileSnapshot.objects.update_or_create(
        user=user,
        repo_url=repo_url,
        path=path,
        sha=sha,
        defaults={
            "content": stored_content,
            "size": size or 0,
            "lines": lines or 0,
        },
    )


def _build_verification_steps(user):
    steps = []
    now = timezone.now()

    personal_complete = all([
        _bool(user.full_name),
        _bool(user.gender),
        _bool(user.phone_number),
        _bool(user.email),
    ])
    academic_complete = all([
        _bool(user.college),
        _bool(user.course),
        _bool(user.branch),
        _bool(user.year_of_study),
    ])
    skills_complete = _bool(user.student_skills)
    github_complete = _bool(user.github_link)
    leetcode_complete = _bool(user.leetcode_link)
    linkedin_profile_complete = _bool(user.linkedin_link) and any([
        _bool(user.linkedin_headline),
        _bool(user.linkedin_about),
        user.linkedin_experience_count,
        user.linkedin_skill_count,
        user.linkedin_cert_count,
    ])
    analysis_ready = user.last_analyzed_at is not None

    steps.append({
        "id": 1,
        "title": "Account created",
        "description": "Your SkillVerify account is active.",
        "status": "completed",
        "completed_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 2,
        "title": "Personal details",
        "description": "Name, gender, phone, and email.",
        "status": "completed" if personal_complete else "in_progress",
        "completed_at": user.date_joined.isoformat() if personal_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 3,
        "title": "Academic profile",
        "description": "College, course, branch, and year.",
        "status": "completed" if academic_complete else "pending",
        "completed_at": user.date_joined.isoformat() if academic_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 4,
        "title": "Skill list",
        "description": "Add the skills you want verified.",
        "status": "completed" if skills_complete else "pending",
        "completed_at": user.date_joined.isoformat() if skills_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 5,
        "title": "Connect GitHub",
        "description": "Link your GitHub to verify project activity.",
        "status": "completed" if github_complete else "pending",
        "completed_at": user.last_analyzed_at.isoformat() if github_complete and user.last_analyzed_at else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 6,
        "title": "Connect LeetCode",
        "description": "Link LeetCode to verify problem solving.",
        "status": "completed" if leetcode_complete else "pending",
        "completed_at": user.last_analyzed_at.isoformat() if leetcode_complete and user.last_analyzed_at else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 7,
        "title": "LinkedIn snapshot",
        "description": "Add headline, about, and experience counts.",
        "status": "completed" if linkedin_profile_complete else "pending",
        "completed_at": user.date_joined.isoformat() if linkedin_profile_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 8,
        "title": "Score analysis",
        "description": "Run AI scoring after linking platforms.",
        "status": "completed" if analysis_ready else "pending",
        "completed_at": user.last_analyzed_at.isoformat() if analysis_ready else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    ai_interview_complete = AIInterviewSession.objects.filter(user=user, status='completed').exists()
    steps.append({
        "id": 9,
        "title": "AI Interview",
        "description": "Complete AI-generated interview questions.",
        "status": "completed" if ai_interview_complete else "pending",
        "completed_at": None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    skill_verification_complete = user.profile_verified or user.skills.filter(verified=True).exists()
    steps.append({
        "id": 10,
        "title": "Skill Verification",
        "description": "Verify skills based on interview performance.",
        "status": "completed" if skill_verification_complete else "pending",
        "completed_at": None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    return steps


def _maybe_mark_profile_verified(user, session):
    total_questions = len(session.questions or [])
    answered = len(session.answers or [])
    if total_questions and answered >= total_questions and not user.profile_verified:
        user.profile_verified = True
        user.save(update_fields=["profile_verified"])


def _build_recommendations(user):
    items = []
    scores = calculate_student_scores(user) if user.role == "student" else {}
    breakdown = score_breakdown(user) if user.role == "student" else {}

    coding_score = scores.get("coding_skill_index", 0)
    communication_score = scores.get("communication_score", 0)
    authenticity_score = scores.get("authenticity_score", 0)
    placement_ready = scores.get("placement_ready", 0)
    placement_parts = breakdown.get("placement_ready", {})

    if placement_ready and placement_ready < 75:
        if placement_parts.get("coding_weighted", 0) < 35:
            items.append({
                "id": 1,
                "title": "Boost coding score for placements",
                "description": "Solve 10 medium LeetCode problems and push 2 GitHub updates.",
                "action_type": "complete_assessment",
                "priority": "high",
                "href": "/dashboard/code-analysis",
                "created_at": "",
            })
        if placement_parts.get("communication_weighted", 0) < 12:
            items.append({
                "id": 2,
                "title": "Improve communication readiness",
                "description": "Complete an AI interview session and update LinkedIn summary.",
                "action_type": "review_roadmap",
                "priority": "medium",
                "href": "/dashboard/ai-interview",
                "created_at": "",
            })
        if placement_parts.get("cgpa_bonus", 0) < 4:
            items.append({
                "id": 4,
                "title": "Add CGPA for placement confidence",
                "description": "Update your CGPA to strengthen academic credibility.",
                "action_type": "review_roadmap",
                "priority": "low",
                "href": "/dashboard/settings",
                "created_at": "",
            })

    if coding_score and coding_score < 70:
        weak = breakdown.get("coding_skill_index", {})
        if weak.get("leetcode_solved_points", 0) < 20:
            items.append({
                "id": 5,
                "title": "Raise LeetCode consistency",
                "description": "Target 5-10 more medium problems to boost coding score.",
                "action_type": "complete_assessment",
                "priority": "high",
                "href": "/dashboard/code-analysis",
                "created_at": "",
            })
    if communication_score and communication_score < 60:
        items.append({
            "id": 7,
            "title": "Strengthen your profile story",
            "description": "Add a strong LinkedIn headline and summary.",
            "action_type": "review_roadmap",
            "priority": "medium",
            "href": "/dashboard/settings",
            "created_at": "",
        })
    if authenticity_score and authenticity_score < 60:
        items.append({
            "id": 8,
            "title": "Diversify verified platforms",
            "description": "Connect one more coding platform to raise authenticity.",
            "action_type": "review_roadmap",
            "priority": "medium",
            "href": "/dashboard/settings",
            "created_at": "",
        })
    if not items:
        items.append({
            "id": 9,
            "title": "Placement readiness stable",
            "description": "Keep weekly submissions and interviews to stay placement-ready.",
            "action_type": "review_roadmap",
            "priority": "low",
            "href": "/dashboard/progress",
            "created_at": "",
        })
    return items


def _extract_github_username(url):
    if not url:
        return None
    try:
        parts = url.strip('/').split('/')
        return parts[-1] if parts else None
    except Exception:
        return None


def _extract_github_repo_owner_and_name(repo_url):
    if not repo_url:
        return None, None
    try:
        parsed = urlparse(repo_url)
    except Exception:
        return None, None
    if parsed.netloc and "github.com" not in parsed.netloc.lower():
        return None, None
    path = parsed.path.strip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return None, None
    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _http_json(method, url, payload=None, headers=None, timeout=10):
    if headers is None:
        headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _github_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "skillsence-ai",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_repo_languages(languages_url, headers):
    if not languages_url:
        return []
    try:
        data = _http_json("GET", languages_url, headers=headers)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    sorted_langs = sorted(data.items(), key=lambda item: item[1], reverse=True)
    return [lang for lang, _ in sorted_langs[:5]]


def _fetch_repo_commits(owner, repo, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=5"
    try:
        data = _http_json("GET", url, headers=headers)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return data


def _fetch_repo_readme(owner, repo, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    readme_headers = dict(headers)
    readme_headers["Accept"] = "application/vnd.github.raw+json"
    try:
        req = urllib.request.Request(url, headers=readme_headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8", errors="ignore")
            return content[:4000]
    except Exception:
        return ""


def _ai_signal_from_text(text):
    lowered = text.lower()
    keywords = ["chatgpt", "copilot", "generated by", "ai generated", "openai", "llm"]
    if any(keyword in lowered for keyword in keywords):
        return 40
    return 0


def _safe_json_loads(text):
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    stripped = text.strip()
    if "```" in stripped:
        parts = stripped.split("```")
        for idx in range(1, len(parts), 2):
            candidate = parts[idx].strip()
            if "\n" in candidate:
                candidate = candidate.split("\n", 1)[1].strip()
            try:
                return json.loads(candidate)
            except Exception:
                continue
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = stripped.find(start_char)
        end = stripped.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start:end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None


def _ai_signal_from_commits(commits):
    score = 0
    for commit in commits:
        message = ((commit.get("commit") or {}).get("message") or "").lower()
        score = max(score, _ai_signal_from_text(message))
    return score


def _analyze_repo(owner, repo):
    headers = _github_headers()
    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    repo_data = _http_json("GET", repo_url, headers=headers)
    if not isinstance(repo_data, dict):
        return None

    languages = _fetch_repo_languages(repo_data.get("languages_url"), headers)
    commits = _fetch_repo_commits(owner, repo, headers)
    readme_text = _fetch_repo_readme(owner, repo, headers)

    ai_score = max(_ai_signal_from_commits(commits), _ai_signal_from_text(readme_text))
    ai_generated = "likely" if ai_score >= 40 else "possible" if ai_score >= 20 else "no_signal"

    copied_or_forked = bool(repo_data.get("fork") or repo_data.get("is_template"))
    originality_score = 70
    if copied_or_forked:
        originality_score = 35
    if repo_data.get("stargazers_count", 0) > 10:
        originality_score += 5
    if repo_data.get("pushed_at"):
        originality_score += 5
    originality_score = min(100, originality_score)

    return {
        "repo_name": repo_data.get("name"),
        "repo_url": repo_data.get("html_url"),
        "description": repo_data.get("description") or "",
        "status": "completed",
        "score": originality_score,
        "metrics": {
            "languages": languages,
            "forked": bool(repo_data.get("fork")),
            "template": bool(repo_data.get("is_template")),
            "ai_generated": ai_generated,
            "ai_confidence": ai_score,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
        },
        "created_at": timezone.now().isoformat(),
    }

def _openai_chat_json(system_content, user_content, max_tokens=700):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions")
    try:
        data = _http_json("POST", url, payload=payload, headers=headers, timeout=20)
    except Exception:
        return None
    try:
        content = (((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
        return _safe_json_loads(content)
    except Exception:
        return None


def _is_text_path(path):
    binary_exts = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
        ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".flac",
        ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".woff", ".woff2",
        ".ttf", ".otf", ".eot", ".exe", ".dll",
    }
    ext = os.path.splitext(path.lower())[1]
    return ext not in binary_exts


def _chunk_text(text, max_chars):
    if max_chars <= 0:
        max_chars = 6000
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        chunks.append(text[start:start + max_chars])
        start += max_chars
    return chunks


def _fetch_repo_tree(owner, repo, headers, default_branch):
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
    return _http_json("GET", tree_url, headers=headers)


def _fetch_blob_text(owner, repo, sha, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{sha}"
    data = _http_json("GET", url, headers=headers)
    if not isinstance(data, dict):
        return None
    if data.get("encoding") != "base64":
        return None
    try:
        decoded = base64.b64decode(data.get("content", ""))
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _openai_score_code_chunk(path, chunk, chunk_index, total_chunks):
    system = (
        "You are a code forensic analyst. Determine likelihood that the provided code "
        "was AI-generated. Return ONLY JSON with keys: score (0-100), label "
        "(likely|possible|unlikely), rationale (short string)."
    )
    user = (
        f"File: {path}\n"
        f"Chunk {chunk_index + 1} of {total_chunks}\n"
        "Analyze the code below:\n\n"
        f"{chunk}"
    )
    result = _openai_chat_json(system, user, max_tokens=220)
    if not isinstance(result, dict):
        return None
    score = result.get("score")
    label = (result.get("label") or "").strip().lower()
    if not isinstance(score, (int, float)):
        return None
    if label not in {"likely", "possible", "unlikely"}:
        return None
    return {
        "score": max(0, min(100, int(score))),
        "label": label,
        "rationale": (result.get("rationale") or "").strip()[:200],
    }


def _analyze_repo_ai_generated(owner, repo, user=None):
    if not os.environ.get("OPENAI_API_KEY"):
        return {"error": "OPENAI_API_KEY not configured."}
    headers = _github_headers()
    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        repo_data = _http_json("GET", repo_url, headers=headers)
    except Exception:
        return {"error": "Unable to fetch repository data."}
    if not isinstance(repo_data, dict):
        return {"error": "Unable to fetch repository data."}

    default_branch = repo_data.get("default_branch") or "main"
    try:
        tree = _fetch_repo_tree(owner, repo, headers, default_branch)
    except Exception:
        return {"error": "Unable to fetch repository tree."}
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        return {"error": "Unable to fetch repository tree."}

    files = []
    for node in tree.get("tree", []):
        if node.get("type") != "blob":
            continue
        path = node.get("path") or ""
        if not path or not _is_text_path(path):
            continue
        files.append({
            "path": path,
            "sha": node.get("sha"),
            "size": node.get("size", 0),
        })

    if not files:
        return {"error": "No text files found for analysis."}

    chunk_chars = int(os.environ.get("AI_REPO_CHUNK_CHARS", "6000") or 6000)
    file_scores = []
    total_weight = 0
    weighted_score = 0
    total_lines = 0

    repo_html_url = repo_data.get("html_url")

    for item in files:
        sha = item.get("sha")
        path = item.get("path")
        if not sha or not path:
            return {"error": "Invalid file metadata."}
        content = _fetch_blob_text(owner, repo, sha, headers)
        if content is None:
            return {"error": f"Failed to load {path}."}
        lines = content.count("\n") + 1 if content else 0
        _store_repo_file_snapshot(
            user=user,
            repo_url=repo_html_url or repo_url,
            path=path,
            sha=sha,
            content=content,
            size=item.get("size", 0),
            lines=lines,
        )
        total_lines += lines
        chunks = _chunk_text(content, chunk_chars)
        if not chunks:
            continue

        chunk_scores = []
        for idx, chunk in enumerate(chunks):
            result = _openai_score_code_chunk(path, chunk, idx, len(chunks))
            if not result:
                return {"error": f"AI analysis failed for {path}."}
            chunk_scores.append((result["score"], len(chunk), result["label"]))

        weighted = sum(score * weight for score, weight, _ in chunk_scores)
        total = sum(weight for _, weight, _ in chunk_scores) or 1
        file_score = int(round(weighted / total))
        file_label = "likely" if file_score >= 70 else "possible" if file_score >= 40 else "unlikely"
        file_scores.append({
            "path": path,
            "score": file_score,
            "label": file_label,
            "lines": lines,
        })
        total_weight += total
        weighted_score += file_score * total

    if total_weight == 0:
        return {"error": "No analyzable files."}

    repo_score = int(round(weighted_score / total_weight))
    repo_label = "likely" if repo_score >= 70 else "possible" if repo_score >= 40 else "unlikely"
    top_files = sorted(file_scores, key=lambda f: f["score"], reverse=True)[:5]

    languages = _fetch_repo_languages(repo_data.get("languages_url"), headers)
    return {
        "repo_name": repo_data.get("name"),
        "repo_url": repo_data.get("html_url"),
        "ai_generated": repo_label,
        "ai_confidence": repo_score,
        "languages": languages,
        "files_analyzed": len(file_scores),
        "lines_analyzed": total_lines,
        "top_ai_files": top_files,
    }

def _question_bank():
    return [
        {"id": 1, "question": "Explain the difference between REST and GraphQL.", "difficulty": "easy", "tags": ["api", "backend"]},
        {"id": 2, "question": "What is a primary key and why is it important?", "difficulty": "easy", "tags": ["sql", "database"]},
        {"id": 3, "question": "How does React manage state updates?", "difficulty": "easy", "tags": ["react", "frontend", "javascript"]},
        {"id": 4, "question": "What is the purpose of indexes in databases?", "difficulty": "medium", "tags": ["sql", "database"]},
        {"id": 5, "question": "Describe how JWT authentication works.", "difficulty": "medium", "tags": ["auth", "backend"]},
        {"id": 6, "question": "What are Python generators and when would you use them?", "difficulty": "medium", "tags": ["python"]},
        {"id": 7, "question": "How do you prevent SQL injection?", "difficulty": "easy", "tags": ["security", "backend"]},
        {"id": 8, "question": "Explain the virtual DOM and its benefits.", "difficulty": "medium", "tags": ["react", "frontend"]},
        {"id": 9, "question": "How would you optimize a slow Django view?", "difficulty": "hard", "tags": ["django", "backend"]},
        {"id": 10, "question": "Describe the time complexity of binary search.", "difficulty": "easy", "tags": ["algorithms"]},
        {"id": 11, "question": "What is the CAP theorem and why does it matter?", "difficulty": "hard", "tags": ["system", "backend"]},
        {"id": 12, "question": "How does caching improve performance? Give an example.", "difficulty": "medium", "tags": ["system", "backend"]},
        {"id": 13, "question": "Explain the difference between PUT and PATCH.", "difficulty": "easy", "tags": ["api", "backend"]},
        {"id": 14, "question": "What are database transactions and ACID properties?", "difficulty": "medium", "tags": ["sql", "database"]},
        {"id": 15, "question": "How would you design a rate limiter for an API?", "difficulty": "hard", "tags": ["system", "backend"]},
        {"id": 16, "question": "Describe the lifecycle methods or hooks in React.", "difficulty": "medium", "tags": ["react", "frontend"]},
        {"id": 17, "question": "What is the difference between synchronous and asynchronous programming?", "difficulty": "easy", "tags": ["general"]},
        {"id": 18, "question": "Explain dependency injection and its benefits.", "difficulty": "medium", "tags": ["backend", "general"]},
        {"id": 19, "question": "How do you handle pagination in an API?", "difficulty": "medium", "tags": ["api", "backend"]},
        {"id": 20, "question": "What are webhooks and when would you use them?", "difficulty": "easy", "tags": ["api"]},
        {"id": 21, "question": "Explain the difference between threads and processes.", "difficulty": "medium", "tags": ["system"]},
        {"id": 22, "question": "How would you structure a scalable file upload system?", "difficulty": "hard", "tags": ["system", "backend"]},
        {"id": 23, "question": "What is CORS and how do you configure it safely?", "difficulty": "easy", "tags": ["security", "frontend", "backend"]},
        {"id": 24, "question": "Describe how you would model a many-to-many relationship.", "difficulty": "easy", "tags": ["database"]},
        {"id": 25, "question": "Explain eventual consistency with an example.", "difficulty": "hard", "tags": ["system"]},
        {"id": 26, "question": "What is memoization and when is it useful?", "difficulty": "medium", "tags": ["algorithms"]},
        {"id": 27, "question": "How do you secure secrets in production?", "difficulty": "medium", "tags": ["security"]},
        {"id": 28, "question": "Explain the difference between SSR and CSR.", "difficulty": "medium", "tags": ["frontend"]},
        {"id": 29, "question": "How would you debug a memory leak in a Node.js app?", "difficulty": "hard", "tags": ["javascript", "backend"]},
        {"id": 30, "question": "Describe how you would design a search feature.", "difficulty": "medium", "tags": ["system", "backend"]},
    ]


def _select_questions_for_user(user, total=10):
    bank = _question_bank()
    skill_names = {skill.name.strip().lower() for skill in user.skills.all() if skill.name}

    def matches(question):
        tags = set(question.get("tags") or [])
        if not tags:
            return True
        return bool(tags & skill_names)

    filtered = [q for q in bank if matches(q)]
    if not filtered:
        filtered = bank

    by_diff = {
        "easy": [q for q in filtered if q["difficulty"] == "easy"],
        "medium": [q for q in filtered if q["difficulty"] == "medium"],
        "hard": [q for q in filtered if q["difficulty"] == "hard"],
    }
    targets = {"easy": 3, "medium": 4, "hard": 3}

    chosen = []
    for level, count in targets.items():
        pool = by_diff.get(level, [])
        if pool:
            chosen.extend(random.sample(pool, min(count, len(pool))))

    if len(chosen) < total:
        remaining = [q for q in filtered if q not in chosen]
        random.shuffle(remaining)
        chosen.extend(remaining[: max(0, total - len(chosen))])

    while len(chosen) < total:
        chosen.append(random.choice(bank))

    random.shuffle(chosen)
    return chosen[:total]


def _intro_questions(user):
    name_hint = user.full_name or "your full name"
    return [
        {
            "id": "intro-1",
            "question": "Welcome! Please tell me your full name and the role you are targeting.",
            "difficulty": "easy",
            "tags": ["intro"],
        },
        {
            "id": "intro-2",
            "question": "Give a brief introduction about yourself, including your current education or experience.",
            "difficulty": "easy",
            "tags": ["intro"],
        },
        {
            "id": "intro-3",
            "question": "Walk me through one project you are proud of and your specific contributions.",
            "difficulty": "easy",
            "tags": ["intro"],
        },
    ]

def _generate_ai_questions(user, total=10):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    skills = [skill.name for skill in user.skills.all() if skill.name]
    prompt = {
        "role": "user",
        "content": (
            f"Generate {total} technical interview questions tailored to this user skill list: "
            f"{', '.join(skills) if skills else 'general software engineering'}. "
            f"Return ONLY a JSON array of {total} objects with keys: question, difficulty, tags. "
            "difficulty must be one of: easy, medium, hard. "
            "Keep questions short."
        ),
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an interview question generator. Return valid JSON only."},
            prompt,
        ],
        "temperature": 0.6,
        "max_tokens": 600,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions")
    try:
        data = _http_json("POST", url, payload=payload, headers=headers, timeout=15)
    except Exception:
        return None
    try:
        content = (((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
        parsed = _safe_json_loads(content)
    except Exception:
        parsed = None

    if not isinstance(parsed, list):
        return None

    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        question = (item.get("question") or "").strip()
        difficulty = (item.get("difficulty") or "").strip().lower()
        tags = item.get("tags") or []
        if not question or difficulty not in {"easy", "medium", "hard"}:
            continue
        cleaned.append({
            "id": len(cleaned) + 1,
            "question": question,
            "difficulty": difficulty,
            "tags": tags if isinstance(tags, list) else [],
        })

    if len(cleaned) < total:
        return None
    return cleaned[:total]


def _select_or_generate_questions(user, total=10):
    intro = _intro_questions(user)
    technical_total = max(0, total - len(intro))
    questions = _generate_ai_questions(user, total=technical_total)
    if questions:
        return intro + questions
    return intro + _select_questions_for_user(user, total=technical_total)


def _score_answer(text, difficulty):
    base = {"easy": 5, "medium": 8, "hard": 12}
    weight = base.get(difficulty, 6)
    word_count = len(text.split())
    length_factor = min(word_count / 40, 1.0)
    keywords = ["api", "db", "database", "cache", "optimize", "complexity", "latency", "index", "security", "auth"]
    keyword_hits = sum(1 for kw in keywords if kw in text.lower())
    keyword_factor = min(keyword_hits / 4, 1.0)
    quality = 0.5 * length_factor + 0.5 * keyword_factor
    score = int(round(weight * (0.4 + 0.6 * quality)))
    return min(weight, max(1, score))


def _max_score(questions):
    base = {"easy": 5, "medium": 8, "hard": 12}
    return sum(base.get(q.get("difficulty"), 6) for q in questions)


def _build_interview_metrics(answers, questions, score):
    answered = len(answers)
    total = max(1, len(questions))
    word_counts = [a.get("word_count", 0) for a in answers] or [0]
    avg_words = sum(word_counts) / len(word_counts)
    clarity = min(100, int(30 + avg_words * 2))
    depth = min(100, int(20 + avg_words * 2.2))
    progress = int(round((answered / total) * 100))
    max_score = max(1, _max_score(questions))
    score_pct = int(round((score / max_score) * 100))
    return [
        {"label": "Interview Score", "value": score_pct, "color": "primary"},
        {"label": "Progress", "value": progress, "color": "accent"},
        {"label": "Clarity", "value": clarity, "color": "primary"},
        {"label": "Depth", "value": depth, "color": "accent"},
    ]


def _build_interview_feedback(answer):
    text = (answer.get("answer") or "").strip()
    word_count = answer.get("word_count", 0)
    filler = sum(text.lower().count(word) for word in ["um", "uh", "like", "basically", "actually"])
    clarity_score = max(0, min(100, int(30 + word_count * 2 - filler * 5)))
    sentiment_score = 0
    for word in ["confident", "achieved", "improved", "delivered", "led", "built", "optimized", "reduced"]:
        if word in text.lower():
            sentiment_score += 1
    sentiment_label = "positive" if sentiment_score >= 2 else "neutral"
    feedback = []
    if word_count < 20:
        feedback.append({"type": "improvement", "text": "Expand with specifics and measurable outcomes."})
    else:
        feedback.append({"type": "strength", "text": "Clear structure with solid context."})
    if clarity_score < 55:
        feedback.append({"type": "improvement", "text": "Slow down and reduce filler words for clarity."})
    else:
        feedback.append({"type": "strength", "text": "Clarity and pacing are strong."})
    if sentiment_label == "positive":
        feedback.append({"type": "strength", "text": "Confident, action-oriented tone."})
    else:
        feedback.append({"type": "improvement", "text": "Add stronger action verbs to increase impact."})
    return feedback


def _build_interview_summary(answers):
    if not answers:
        return {"strengths": ["Willing to engage in the interview."], "improvements": ["Provide more detail."]}
    avg_words = sum(a.get("word_count", 0) for a in answers) / max(1, len(answers))
    strengths = []
    improvements = []
    if avg_words >= 35:
        strengths.append("Strong detail and context in responses.")
    else:
        improvements.append("Add more depth with examples and metrics.")
    if any("project" in (a.get("answer") or "").lower() for a in answers):
        strengths.append("Good use of project-based explanations.")
    else:
        improvements.append("Reference a concrete project to back up your claims.")
    if not strengths:
        strengths.append("Consistent participation across questions.")
    if not improvements:
        improvements.append("Keep answers concise and structured.")
    return {"strengths": strengths, "improvements": improvements}


def _generate_followup_question(answer, current_question):
    prompt = (
        "Generate one short follow-up interview question based on this candidate answer. "
        "Return JSON with keys: question, difficulty. difficulty must be easy or medium."
    )
    user = f"Question: {current_question}\nAnswer: {answer}\n"
    result = _openai_chat_json(prompt, user, max_tokens=120)
    if isinstance(result, dict):
        question = (result.get("question") or "").strip()
        difficulty = (result.get("difficulty") or "easy").strip().lower()
        if question and difficulty in {"easy", "medium"}:
            return {"id": f"followup-{random.randint(1000, 9999)}", "question": question, "difficulty": difficulty, "tags": ["followup"]}
    if len(answer.split()) < 25:
        return {
            "id": f"followup-{random.randint(1000, 9999)}",
            "question": "Can you add more detail and a concrete example to support that?",
            "difficulty": "easy",
            "tags": ["followup"],
        }
    return None


def _build_interview_tips(answers):
    if not answers:
        return ["Keep answers structured: context, action, result.", "Mention measurable impact when possible."]
    last = answers[-1].get("difficulty")
    if last == "hard":
        return ["Break complex problems into smaller parts.", "Highlight trade-offs and constraints."]
    if last == "medium":
        return ["Explain your approach before details.", "Mention edge cases you considered."]
    return ["Use simple, concise explanations.", "Offer a quick example to reinforce the idea."]


def _interview_state_payload(session):
    questions = session.questions or []
    total = len(questions)
    index = session.current_index
    current = None
    if 0 <= index < total:
        current = questions[index]
    max_score = max(1, _max_score(questions))
    score_pct = int(round((session.score / max_score) * 100)) if questions else 0
    return {
        "total_questions": total,
        "current_index": index,
        "current_question": current.get("question") if current else None,
        "current_difficulty": current.get("difficulty") if current else None,
        "score": score_pct,
    }

def _flag_ai_generated_repos(owner, user=None):
    headers = _github_headers()
    repos_url = f"https://api.github.com/users/{owner}/repos?per_page=100&sort=updated"
    try:
        repos = _http_json("GET", repos_url, headers=headers)
    except Exception:
        return []

    flagged = []
    if isinstance(repos, list):
        for repo in repos:
            repo_name = repo.get("name")
            if not repo_name:
                continue
            analysis = _analyze_repo_ai_generated(owner, repo_name, user=user)
            if not analysis:
                continue
            if analysis.get("error"):
                flagged.append({
                    "repo_name": repo_name,
                    "repo_url": repo.get("html_url"),
                    "status": "failed",
                    "error": analysis.get("error"),
                })
                continue
            if analysis.get("ai_generated") in {"likely", "possible"}:
                flagged.append({
                    "repo_name": analysis.get("repo_name"),
                    "repo_url": analysis.get("repo_url"),
                    "ai_generated": analysis.get("ai_generated"),
                    "ai_confidence": analysis.get("ai_confidence", 0),
                    "languages": analysis.get("languages", []),
                    "files_analyzed": analysis.get("files_analyzed", 0),
                    "lines_analyzed": analysis.get("lines_analyzed", 0),
                    "top_ai_files": analysis.get("top_ai_files", []),
                })
    return flagged

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    user = request.user
    skills = SkillSerializer(user.skills.all(), many=True).data
    activities = ActivitySerializer(user.activities.all()[:10], many=True).data
    scorecards = ScoreCardSerializer(user.scorecards.all(), many=True).data
    steps = VerificationStepSerializer(user.verification_steps.all(), many=True).data
    return Response({
        'skills': skills,
        'activities': activities,
        'scorecards': scorecards,
        'verification_steps': steps,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activities_view(request):
    activities = ActivitySerializer(request.user.activities.all()[:20], many=True).data
    return Response(activities)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_steps_view(request):
    steps = list(request.user.verification_steps.all())
    if steps:
        return Response(VerificationStepSerializer(steps, many=True).data)
    return Response(_build_verification_steps(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations_view(request):
    return Response(_build_recommendations(request.user))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_generated_repos_view(request):
    owner = _extract_github_username(request.user.github_link)
    if not owner:
        return Response({'items': [], 'analyzed_at': None})
    items = _flag_ai_generated_repos(owner, user=request.user)
    analyzed_at = timezone.now()
    request.user.last_analyzed_at = analyzed_at
    request.user.save(update_fields=["last_analyzed_at"])
    return Response({'items': items, 'analyzed_at': analyzed_at.isoformat()})


@api_view(['GET'])
@permission_classes([AllowAny])
def skill_suggestions_view(request):
    skills = Skill.objects.values_list('name', flat=True).distinct().order_by('name')[:50]
    if skills:
        return Response(list(skills))
    block = ContentBlock.objects.filter(key='skill_suggestions').first()
    if block and isinstance(block.payload, list):
        return Response(block.payload)
    return Response([])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skill_passport_view(request):
    skills = request.user.skills.all()
    radar_data = [
        {'skill': skill.name, 'level': skill.score or 50, 'fullMark': 100}
        for skill in skills
    ]
    verified = [
        {
            'name': skill.name,
            'level': skill.level,
            'evidence': 0,
            'verified': skill.verified,
        }
        for skill in skills.filter(verified=True)
    ]
    scorecards = ScoreCard.objects.filter(user=request.user)
    bar_data = [
        {'name': score.score_type.replace('_', ' ').title(), 'score': score.score}
        for score in scorecards
    ]
    return Response({
        'radar_data': radar_data,
        'bar_data': bar_data,
        'verified_skills': verified,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skill_passport_pdf_view(request):
    user = request.user
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return Response(
            {'error': 'PDF export requires the reportlab package.'},
            status=500,
        )
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        matplotlib_available = True
    except Exception:
        matplotlib_available = False

    skills = user.skills.all()
    scorecards = ScoreCard.objects.filter(user=user)
    scores = {card.score_type: card.score for card in scorecards}

    cutoff = timezone.localdate() - timedelta(days=90)
    series = list(user.score_snapshots.filter(recorded_on__gte=cutoff).order_by("recorded_on"))

    def render_chart(fig):
        chart_buffer = io.BytesIO()
        fig.savefig(chart_buffer, format="png", dpi=120, bbox_inches="tight")
        if matplotlib_available:
            plt.close(fig)
        chart_buffer.seek(0)
        return chart_buffer

    def chart_scores():
        if not matplotlib_available:
            return None
        labels = ["Coding", "Communication", "Authenticity", "Placement"]
        values = [
            scores.get("coding_skill_index", 0),
            scores.get("communication_score", 0),
            scores.get("authenticity_score", 0),
            scores.get("placement_ready", 0),
        ]
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.bar(labels, values, color=["#2563eb", "#10b981", "#f59e0b", "#0ea5e9"])
        ax.set_ylim(0, 100)
        ax.set_title("Core Scores")
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        for idx, value in enumerate(values):
            ax.text(idx, value + 2, str(value), ha="center", fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        return render_chart(fig)

    def chart_trend():
        if not matplotlib_available:
            return None
        if not series:
            return None
        dates = [snap.recorded_on for snap in series]
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.plot(dates, [snap.scores.get("placement_ready", 0) for snap in series], label="Placement", color="#0ea5e9")
        ax.plot(dates, [snap.scores.get("coding_skill_index", 0) for snap in series], label="Coding", color="#2563eb")
        ax.set_ylim(0, 100)
        ax.set_title("90 Day Trend")
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=7, loc="upper left")
        ax.spines[["top", "right"]].set_visible(False)
        return render_chart(fig)

    def chart_radar():
        if not matplotlib_available:
            return None
        top = sorted(skills, key=lambda s: s.score or 0, reverse=True)[:6]
        if not top:
            return None
        labels = [skill.name for skill in top]
        values = [skill.score or 0 for skill in top]
        angles = [n / len(labels) * 2 * math.pi for n in range(len(labels))]
        values = values + [values[0]]
        angles = angles + [angles[0]]
        fig = plt.figure(figsize=(4, 3))
        ax = plt.subplot(111, polar=True)
        ax.plot(angles, values, color="#2563eb", linewidth=2)
        ax.fill(angles, values, color="#2563eb", alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylim(0, 100)
        ax.set_title("Skill Radar", y=1.08)
        return render_chart(fig)

    def chart_verified():
        if not matplotlib_available:
            return None
        total = skills.count()
        verified = skills.filter(verified=True).count()
        if total == 0:
            return None
        fig, ax = plt.subplots(figsize=(3.5, 2.4))
        ax.pie([verified, max(0, total - verified)], labels=["Verified", "Unverified"], autopct="%1.0f%%", textprops={"fontsize": 7})
        ax.set_title("Verification Mix")
        return render_chart(fig)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 0.75 * inch
    y = height - x_margin

    pdf.setTitle("SkillVerify Skill Passport")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(x_margin, y, "SkillVerify Skill Passport")
    y -= 0.3 * inch

    pdf.setFont("Helvetica", 10)
    pdf.drawString(x_margin, y, f"Name: {user.full_name or user.username}")
    y -= 0.18 * inch
    pdf.drawString(x_margin, y, f"Email: {user.email}")
    y -= 0.18 * inch
    profile_line = " - ".join([value for value in [user.course, user.college] if value])
    pdf.drawString(x_margin, y, f"Profile: {profile_line or '-'}")
    y -= 0.3 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_margin, y, "Core Scores")
    y -= 0.2 * inch

    bar_chart = chart_scores()
    if bar_chart:
        pdf.drawImage(ImageReader(bar_chart), x_margin, y - 2.2 * inch, width=6.5 * inch, height=2.2 * inch)
        y -= 2.5 * inch
    else:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x_margin, y, "Charts unavailable (matplotlib not installed).")
        y -= 0.3 * inch

    y -= 0.2 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_margin, y, "Verified Skills")
    y -= 0.2 * inch
    pdf.setFont("Helvetica", 10)
    if not skills:
        pdf.drawString(x_margin, y, "No skills verified yet.")
        y -= 0.18 * inch
    else:
        for skill in skills:
            pdf.drawString(x_margin, y, f"{skill.name} - {skill.level} ({skill.score}/100)")
            y -= 0.18 * inch
            if y < 1.2 * inch:
                pdf.showPage()
                y = height - x_margin
                pdf.setFont("Helvetica", 10)

    y -= 0.2 * inch
    radar = chart_radar()
    if radar:
        pdf.drawImage(ImageReader(radar), x_margin, y - 3 * inch, width=4 * inch, height=3 * inch)
    verified_chart = chart_verified()
    if verified_chart:
        pdf.drawImage(ImageReader(verified_chart), x_margin + 4.2 * inch, y - 2.4 * inch, width=2.3 * inch, height=2.3 * inch)

    y -= 3.2 * inch
    trend = chart_trend()
    if trend:
        if y < 2.6 * inch:
            pdf.showPage()
            y = height - x_margin
        pdf.drawImage(ImageReader(trend), x_margin, y - 2.2 * inch, width=6.5 * inch, height=2.2 * inch)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="skillverify-passport.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_interview_view(request):
    session = AIInterviewSession.objects.filter(user=request.user).first()
    if not session:
        return Response({
            'status': 'idle',
            'transcript': [],
            'feedback': [],
            'metrics': [],
            'tips': [],
            **_interview_state_payload(AIInterviewSession(user=request.user)),
        })
    return Response({
        'status': session.status,
        'transcript': session.transcript,
        'feedback': session.feedback,
        'metrics': session.metrics,
        'tips': session.tips,
        **_interview_state_payload(session),
        'updated_at': session.updated_at.isoformat(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_interview_action_view(request):
    action = request.data.get('action')
    if action == 'start':
        questions = _select_or_generate_questions(request.user, total=10)
        if not questions:
            return Response({'error': 'AI question generation failed'}, status=502)
        first = questions[0] if questions else None
        metrics = _build_interview_metrics([], questions, 0)
        tips = _build_interview_tips([])
        session = AIInterviewSession.objects.create(
            user=request.user,
            transcript=[{
                'speaker': 'AI',
                'text': first.get('question') if first else 'Tell me about a recent project you built.',
                'difficulty': first.get('difficulty') if first else 'easy',
                'question_index': 0,
            }],
            questions=questions,
            answers=[],
            current_index=0,
            score=0,
            metrics=metrics,
            tips=tips,
        )
        return Response({
            'status': session.status,
            'transcript': session.transcript,
            'feedback': session.feedback,
            'metrics': metrics,
            'tips': tips,
            **_interview_state_payload(session),
        })

    session = AIInterviewSession.objects.filter(user=request.user, status='active').first()
    if not session:
        return Response({'error': 'No active session'}, status=400)

    if action == 'respond':
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'error': 'Message required'}, status=400)
        questions = session.questions or []
        if not questions:
            return Response({'error': 'No questions available'}, status=400)

        index = session.current_index
        if index >= len(questions):
            return Response({'error': 'Interview already completed'}, status=400)

        current = questions[index]
        word_count = len(message.split())
        points = _score_answer(message, current.get("difficulty"))

        answers = list(session.answers or [])
        answers.append({
            "question": current.get("question"),
            "difficulty": current.get("difficulty"),
            "answer": message,
            "word_count": word_count,
            "points": points,
        })

        transcript = list(session.transcript or [])
        transcript.append({
            'speaker': 'You',
            'text': message,
            'difficulty': current.get("difficulty"),
            'question_index': index,
        })

        session.score = (session.score or 0) + points

        followup = _generate_followup_question(message, current.get("question"))
        if followup:
            questions.insert(index + 1, followup)

        if index + 1 < len(questions):
            next_q = questions[index + 1]
            transcript.append({
                'speaker': 'AI',
                'text': next_q.get('question'),
                'difficulty': next_q.get('difficulty'),
                'question_index': index + 1,
            })
            session.current_index = index + 1
        else:
            summary = _build_interview_summary(answers)
            session.status = 'completed'
            session.completed_at = timezone.now()
            transcript.append({
                'speaker': 'AI',
                'text': (
                    "Interview completed. Summary:\n"
                    f"Strengths: {', '.join(summary['strengths'])}. "
                    f"Improvements: {', '.join(summary['improvements'])}."
                ),
                'difficulty': 'summary',
                'question_index': index,
            })

        session.answers = answers
        session.questions = questions
        session.transcript = transcript
        session.metrics = _build_interview_metrics(answers, questions, session.score)
        session.feedback = _build_interview_feedback(answers[-1])
        session.tips = _build_interview_tips(answers)
        session.save(update_fields=[
            'answers',
            'transcript',
            'questions',
            'metrics',
            'feedback',
            'tips',
            'score',
            'current_index',
            'status',
            'completed_at',
            'updated_at',
        ])
        if session.status == 'completed':
            _maybe_mark_profile_verified(request.user, session)

        return Response({
            'status': session.status,
            'transcript': session.transcript,
            'feedback': session.feedback,
            'metrics': session.metrics,
            'tips': session.tips,
            **_interview_state_payload(session),
        })

    if action == 'finish':
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at', 'updated_at'])
        _maybe_mark_profile_verified(request.user, session)
        return Response({'status': session.status, **_interview_state_payload(session)})

    return Response({'error': 'Invalid action'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recruiter_dashboard_view(request):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)
    students = User.objects.filter(role='student').select_related()
    candidates = []
    for student in students[:20]:
        scores = {
            card.score_type: card.score
            for card in student.scorecards.all()
        }
        skill_list = [
            {'name': skill.name, 'score': skill.score or 50}
            for skill in student.skills.all()[:6]
        ]
        candidates.append({
            'id': student.id,
            'name': student.full_name or student.username,
            'college': student.college or '',
            'role': student.course or 'Student',
            'location': student.branch or '',
            'score': scores.get('placement_ready', 0),
            'skills': skill_list,
        })
    return Response({
        'candidates': candidates,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def university_dashboard_view(request):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)
    students = User.objects.filter(role='student')
    totals = students.count()
    avg_score = ScoreCard.objects.filter(score_type='placement_ready').aggregate(avg=Avg('score'))['avg'] or 0
    skill_counts = Skill.objects.values('name').annotate(count=Count('id')).order_by('-count')[:6]
    return Response({
        'summary': {
            'students': totals,
            'average_ready': round(avg_score, 1),
        },
        'skill_distribution': list(skill_counts),
    })




@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def code_analysis_view(request):
    if request.method == 'POST':
        repo_url = (request.data.get('repo_url') or '').strip()
        if not repo_url:
            return Response({'error': 'Repository URL is required'}, status=400)
        owner, repo_name = _extract_github_repo_owner_and_name(repo_url)
        if not owner:
            owner = _extract_github_username(request.user.github_link)
        if not owner or not repo_name:
            return Response({'error': 'Valid GitHub repository URL is required'}, status=400)
        analysis = None
        ai_error = None
        if os.environ.get("OPENAI_API_KEY"):
            try:
                analysis = _analyze_repo_ai_generated(owner, repo_name, user=request.user)
            except Exception:
                analysis = None
            if isinstance(analysis, dict) and analysis.get("error"):
                ai_error = analysis.get("error")
                analysis = None
        else:
            ai_error = "OPENAI_API_KEY not configured."

        if not analysis:
            return Response({'error': ai_error or 'Unable to analyze repository'}, status=400)

        metrics = {
            "ai_generated": analysis.get("ai_generated"),
            "ai_confidence": analysis.get("ai_confidence", 0),
            "languages": analysis.get("languages", []),
            "files_analyzed": analysis.get("files_analyzed", 0),
            "lines_analyzed": analysis.get("lines_analyzed", 0),
        }
        top_files = analysis.get("top_ai_files") or []
        if isinstance(top_files, list):
            formatted = []
            for item in top_files:
                if isinstance(item, dict):
                    path = item.get("path") or "unknown"
                    score = item.get("score", 0)
                    label = item.get("label")
                    suffix = f"{score}" if label is None else f"{score} ({label})"
                    formatted.append(f"{path} - {suffix}")
                else:
                    formatted.append(str(item))
            if formatted:
                metrics["top_ai_files"] = formatted

        report, _ = CodeAnalysisReport.objects.update_or_create(
            user=request.user,
            repo_url=analysis['repo_url'],
            defaults={
                'summary': 'AI-generated likelihood analysis.',
                'score': metrics["ai_confidence"],
                'metrics': metrics,
                'status': 'completed',
            },
        )
        return Response({
            "id": report.id,
            "repo_name": analysis.get("repo_name"),
            "repo_url": analysis.get("repo_url"),
            "description": report.summary,
            "score": report.score,
            "metrics": report.metrics,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
        })

    items = []
    for report in CodeAnalysisReport.objects.filter(user=request.user):
        repo_name = report.repo_url.rstrip('/').split('/')[-1]
        items.append({
            'id': report.id,
            'repo_name': repo_name,
            'repo_url': report.repo_url,
            'description': report.summary,
            'score': report.score,
            'metrics': report.metrics,
            'status': report.status,
            'created_at': report.created_at.isoformat(),
        })
    return Response({'items': items})




@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def media_view(request):
    if request.method == 'POST':
        upload = request.FILES.get('file')
        title = (request.data.get('title') or '').strip()
        media_type = (request.data.get('media_type') or '').strip()
        if not upload or not media_type:
            return Response({'error': 'File and media_type are required'}, status=400)
        if media_type not in ['video', 'audio']:
            return Response({'error': 'media_type must be video or audio'}, status=400)
        if not title:
            title = upload.name
        media = MediaUpload.objects.create(
            user=request.user,
            title=title,
            media_type=media_type,
            file=upload,
            status='ready',
        )
        return Response({
            'id': media.id,
            'title': media.title,
            'media_type': media.media_type,
            'status': media.status,
            'file_url': media.file.url,
            'created_at': media.created_at.isoformat(),
        })
    items = [
        {
            'id': item.id,
            'title': item.title,
            'media_type': item.media_type,
            'status': item.status,
            'file_url': item.file.url,
            'created_at': item.created_at.isoformat(),
        }
        for item in MediaUpload.objects.filter(user=request.user)
    ]
    return Response({'items': items})




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def progress_view(request):
    cutoff = timezone.localdate() - timedelta(days=90)
    snapshots = ScoreSnapshot.objects.filter(user=request.user, recorded_on__gte=cutoff).order_by('recorded_on')
    series = [
        {
            'date': snap.recorded_on.isoformat(),
            **(snap.scores or {}),
        }
        for snap in snapshots
    ]
    streak = 0
    if snapshots.exists():
        dates = {snap.recorded_on for snap in snapshots}
        day = timezone.localdate()
        while day in dates:
            streak += 1
            day = day - timedelta(days=1)
    milestones = {
        'skills': request.user.skills.count(),
    }
    return Response({
        'series': series,
        'streak': streak,
        'milestones': milestones,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def roadmap_view(request):
    scores = calculate_student_scores(request.user) if request.user.role == 'student' else {}
    items = []
    if scores.get('coding_skill_index', 0) < 70:
        items.append({
            'title': 'Algorithm mastery sprint',
            'description': 'Solve 15 medium problems over 3 weeks.',
            'status': 'in_progress',
        })
    if scores.get('communication_score', 0) < 70:
        items.append({
            'title': 'Profile narrative upgrade',
            'description': 'Refine LinkedIn summary and add 2 experience bullets.',
            'status': 'pending',
        })
    if not items:
        items.append({
            'title': 'Maintain momentum',
            'description': 'Keep shipping weekly updates to sustain your scores.',
            'status': 'completed',
        })
    return Response({'items': items})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def settings_view(request):
    return Response({'settings': {}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_view(request):
    user = request.user
    if user.role != "student":
        return Response({"series": []})

    cutoff = timezone.localdate() - timedelta(days=90)
    snapshots = ScoreSnapshot.objects.filter(user=user, recorded_on__gte=cutoff).order_by("recorded_on")

    if not snapshots.exists():
        scores = upsert_scorecards(user)
        today = timezone.localdate()
        ScoreSnapshot.objects.update_or_create(
            user=user,
            recorded_on=today,
            defaults={"scores": scores},
        )
        snapshots = ScoreSnapshot.objects.filter(user=user, recorded_on__gte=cutoff).order_by("recorded_on")

    series = []
    for snapshot in snapshots:
        scores = snapshot.scores or {}
        series.append({
            "date": snapshot.recorded_on.isoformat(),
            "coding_skill_index": scores.get("coding_skill_index", 0),
            "communication_score": scores.get("communication_score", 0),
            "authenticity_score": scores.get("authenticity_score", 0),
            "placement_ready": scores.get("placement_ready", 0),
        })

    return Response({"series": series})
