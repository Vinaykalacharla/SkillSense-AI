from datetime import timedelta
import csv
import io
import math
import json
import os
import base64
import re
import textwrap
import urllib.request
import urllib.error
from urllib.parse import urlparse
import random
from django.db import transaction
from django.db.models import Avg, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.http import FileResponse, HttpResponse

from .models import (
    Skill,
    Activity,
    ScoreCard,
    VerificationStep,
    ScoreSnapshot,
    Document,
    InterviewSchedule,
    AIInterviewSession,
    CodeAnalysisReport,
    MediaUpload,
    Notification,
    PlacementDrive,
    ProjectSubmission,
    RecruiterCandidatePipeline,
    RecruiterJob,
    RecruiterSavedSearch,
    RepoFileSnapshot,
    InterventionRecord,
    UniversityBatchUpload,
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


def _score_mean(values):
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_string_list(raw_value):
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        items = raw_value
    elif isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                loaded = json.loads(text)
                if isinstance(loaded, list):
                    items = loaded
                else:
                    items = [text]
            except json.JSONDecodeError:
                items = text.replace("\n", ",").replace(";", ",").split(",")
        else:
            items = text.replace("\n", ",").replace(";", ",").split(",")
    else:
        items = [raw_value]

    cleaned = []
    seen = set()
    for item in items:
        normalized = str(item or "").strip()
        if not normalized:
            continue
        dedupe_key = normalized.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        cleaned.append(normalized)
    return cleaned


def _tokenize_match_text(text):
    if not text:
        return set()
    tokens = re.findall(r"[a-z0-9+#.]{2,}", str(text).lower())
    stopwords = {
        "and", "the", "for", "with", "from", "that", "this", "have", "will", "your",
        "role", "team", "work", "years", "year", "using", "build", "built", "into",
        "about", "need", "plus", "more", "must", "able", "good", "strong", "skills",
        "experience", "candidate", "student", "project", "projects", "company",
    }
    return {token for token in tokens if token not in stopwords}


def _candidate_match_corpus(student, candidate_payload=None):
    payload = candidate_payload or _student_summary_payload(student)
    parts = [
        student.student_skills or "",
        student.linkedin_headline or "",
        student.linkedin_about or "",
        " ".join(skill.get("name", "") for skill in payload.get("skills", [])),
        " ".join(payload.get("highlights", [])),
    ]
    latest_report = student.code_analysis_reports.filter(status='completed').first()
    if latest_report:
        parts.extend([latest_report.summary or "", latest_report.repo_url or ""])
    latest_submission = student.submissions.first()
    if latest_submission:
        parts.extend([latest_submission.title or "", latest_submission.description or "", latest_submission.repo_url or ""])
    latest_interview = student.ai_interviews.filter(status='completed').first()
    if latest_interview:
        answers = latest_interview.answers or []
        parts.extend(answer.get("answer", "") for answer in answers[:5] if isinstance(answer, dict))
    return " ".join(filter(None, parts))


def _job_tokens(job):
    return _tokenize_match_text(
        " ".join(
            [
                job.title or "",
                job.description or "",
                " ".join(_normalize_string_list(job.required_skills)),
                " ".join(_normalize_string_list(job.preferred_skills)),
            ]
        )
    )


def _semantic_overlap(job, student, candidate_payload=None):
    candidate_tokens = _tokenize_match_text(_candidate_match_corpus(student, candidate_payload))
    job_tokens = _job_tokens(job)
    if not job_tokens:
        return {
            "score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
        }
    matched = sorted(job_tokens & candidate_tokens)
    missing = sorted(job_tokens - candidate_tokens)
    score = round((len(matched) / max(1, len(job_tokens))) * 100)
    return {
        "score": score,
        "matched_keywords": matched[:8],
        "missing_keywords": missing[:8],
    }


def _create_notification(user, title, message, category="system", link="", metadata=None):
    if not user:
        return None
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        category=category,
        link=link,
        metadata=metadata or {},
    )


def _notification_payload(notification):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "category": notification.category,
        "link": notification.link,
        "metadata": notification.metadata or {},
        "read": bool(notification.read_at),
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def _bootstrap_notifications_for_user(user):
    if Notification.objects.filter(user=user).exists():
        return

    if _require_role(user, "student"):
        _create_notification(
            user,
            "Complete your passport",
            "Add more verified evidence to strengthen your skill passport.",
            category="student",
            link="/dashboard/passport",
        )
        if not user.profile_verified:
            _create_notification(
                user,
                "Interview pending",
                "Finish the AI interview to unlock a verified profile.",
                category="verification",
                link="/dashboard/interview",
            )
        if not _latest_resume_document(user):
            _create_notification(
                user,
                "Resume builder ready",
                "Generate an ATS-friendly resume from your verified profile.",
                category="student",
                link="/dashboard/resume-builder",
            )
    elif _require_role(user, "recruiter"):
        _create_notification(
            user,
            "Create your first job brief",
            "Add a job description to rank candidates by match score.",
            category="recruiter",
            link="/recruiter/dashboard",
        )
    elif _require_role(user, "university"):
        _create_notification(
            user,
            "Import your batch",
            "Upload a cohort CSV to populate students and intervention tracking.",
            category="university",
            link="/university/dashboard",
        )


def _candidate_pipeline_payload(entry):
    if not entry:
        return None
    return {
        "status": entry.status,
        "notes": entry.notes,
        "tags": entry.tags or [],
        "match_score": int(entry.match_score or 0),
        "assignee_name": entry.assignee_name,
        "next_step": entry.next_step,
        "rejection_reason": entry.rejection_reason,
        "follow_up_at": entry.follow_up_at.isoformat() if entry.follow_up_at else None,
        "last_contacted_at": entry.last_contacted_at.isoformat() if entry.last_contacted_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def _pipeline_summary_for_entries(entries):
    summary = {
        "sourced": 0,
        "shortlisted": 0,
        "interviewing": 0,
        "offered": 0,
        "rejected": 0,
    }
    for entry in entries:
        if entry.status in summary:
            summary[entry.status] += 1
    return summary


def _job_match_payload(candidate_payload, job, student=None):
    if not job:
        return {
            "score": candidate_payload.get("score", 0),
            "reasons": [],
            "matched_skills": [],
            "missing_skills": [],
            "semantic_score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
        }

    candidate_skills = {
        (skill.get("name") or "").strip().lower(): skill
        for skill in candidate_payload.get("skills", [])
        if skill.get("name")
    }
    required = _normalize_string_list(job.required_skills)
    preferred = _normalize_string_list(job.preferred_skills)
    matched_required = [skill for skill in required if skill.lower() in candidate_skills]
    matched_preferred = [skill for skill in preferred if skill.lower() in candidate_skills]
    missing_required = [skill for skill in required if skill.lower() not in candidate_skills]

    required_ratio = len(matched_required) / max(1, len(required)) if required else min(
        1,
        (candidate_payload.get("scores", {}).get("coding_skill_index", 0) or 0) / 100,
    )
    preferred_ratio = len(matched_preferred) / max(1, len(preferred)) if preferred else 0.5
    ready_ratio = min(1, (candidate_payload.get("score", 0) or 0) / 100)
    min_ready_bonus = 1 if (candidate_payload.get("score", 0) or 0) >= int(job.min_ready_score or 0) else 0
    authenticity_ratio = min(
        1,
        (candidate_payload.get("scores", {}).get("authenticity_score", 0) or 0) / 100,
    )
    verified_bonus = 1 if candidate_payload.get("profile_verified") else 0
    semantic = _semantic_overlap(job, student, candidate_payload) if student else {"score": 0, "matched_keywords": [], "missing_keywords": []}
    semantic_ratio = min(1, (semantic.get("score", 0) or 0) / 100)

    match_score = round(
        min(
            100,
            (
                required_ratio * 35
                + preferred_ratio * 10
                + ready_ratio * 15
                + min_ready_bonus * 15
                + authenticity_ratio * 5
                + verified_bonus * 5
                + semantic_ratio * 15
            ),
        )
    )

    reasons = []
    if matched_required:
        reasons.append(f"Matched required skills: {', '.join(matched_required[:3])}.")
    if (candidate_payload.get("score", 0) or 0) >= int(job.min_ready_score or 0):
        reasons.append(f"Placement readiness clears the {job.min_ready_score} threshold.")
    if candidate_payload.get("profile_verified"):
        reasons.append("Profile is verification-complete.")
    if missing_required:
        reasons.append(f"Still missing: {', '.join(missing_required[:3])}.")
    if semantic.get("matched_keywords"):
        reasons.append(f"Semantic overlap detected in: {', '.join(semantic['matched_keywords'][:3])}.")

    return {
        "score": match_score,
        "reasons": reasons[:3],
        "matched_skills": matched_required,
        "missing_skills": missing_required,
        "semantic_score": semantic.get("score", 0),
        "matched_keywords": semantic.get("matched_keywords", []),
        "missing_keywords": semantic.get("missing_keywords", []),
    }


def _job_payload(job):
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "required_skills": _normalize_string_list(job.required_skills),
        "preferred_skills": _normalize_string_list(job.preferred_skills),
        "min_ready_score": int(job.min_ready_score or 0),
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _interview_schedule_payload(schedule):
    return {
        "id": schedule.id,
        "title": schedule.title,
        "candidate_id": schedule.candidate_id,
        "candidate_name": schedule.candidate.full_name or schedule.candidate.username,
        "recruiter_id": schedule.recruiter_id,
        "recruiter_name": schedule.recruiter.full_name or schedule.recruiter.username,
        "job_id": schedule.job_id,
        "job_title": schedule.job.title if schedule.job else "",
        "scheduled_at": schedule.scheduled_at.isoformat() if schedule.scheduled_at else None,
        "duration_minutes": schedule.duration_minutes,
        "meeting_link": schedule.meeting_link,
        "notes": schedule.notes,
        "status": schedule.status,
    }


def _saved_search_payload(saved_search):
    return {
        "id": saved_search.id,
        "name": saved_search.name,
        "query": saved_search.query,
        "filters": saved_search.filters or {},
        "updated_at": saved_search.updated_at.isoformat() if saved_search.updated_at else None,
    }


def _batch_upload_payload(batch_upload):
    return {
        "id": batch_upload.id,
        "filename": batch_upload.filename,
        "status": batch_upload.status,
        "summary": batch_upload.summary or {},
        "created_at": batch_upload.created_at.isoformat() if batch_upload.created_at else None,
    }


def _intervention_record_payload(record):
    if not record:
        return None
    return {
        "status": record.status,
        "priority": record.priority,
        "note": record.note,
        "recommended_action": record.recommended_action,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _placement_drive_payload(drive, students=None):
    eligible_students = []
    if students is not None:
        for item in students:
            branch_match = not drive.target_branches or item.get("branch") in drive.target_branches
            course_match = not drive.target_courses or item.get("course") in drive.target_courses
            score_match = item.get("score", 0) >= int(drive.minimum_ready_score or 0)
            if branch_match and course_match and score_match:
                eligible_students.append(item)
    return {
        "id": drive.id,
        "company_name": drive.company_name,
        "role_title": drive.role_title,
        "description": drive.description,
        "target_branches": _normalize_string_list(drive.target_branches),
        "target_courses": _normalize_string_list(drive.target_courses),
        "minimum_ready_score": int(drive.minimum_ready_score or 0),
        "scheduled_on": drive.scheduled_on.isoformat() if drive.scheduled_on else None,
        "status": drive.status,
        "eligible_count": len(eligible_students),
        "top_candidates": [
            {
                "id": item["id"],
                "name": item["name"],
                "score": item["score"],
                "branch": item["branch"],
                "verification_id": item["verification_id"],
            }
            for item in sorted(eligible_students, key=lambda entry: (-entry["score"], entry["name"].lower()))[:5]
        ],
        "updated_at": drive.updated_at.isoformat() if drive.updated_at else None,
    }


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
        _create_notification(
            user,
            "Profile verified",
            "Your AI interview is complete and your profile is now verified.",
            category="verification",
            link="/dashboard/passport",
        )


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


def _student_score_map(student):
    score_map = {
        card.score_type: card.score
        for card in student.scorecards.all()
    }
    if score_map:
        return score_map
    if student.role != "student":
        return {}
    try:
        return calculate_student_scores(student)
    except Exception:
        return {}


def _student_skill_payload(student):
    skill_objects = sorted(
        list(student.skills.all()),
        key=lambda skill: (-(skill.score or 0), skill.name.lower()),
    )
    skills = [
        {
            "name": skill.name,
            "score": skill.score or 0,
            "level": skill.level,
            "verified": skill.verified,
        }
        for skill in skill_objects
    ]
    if skills:
        return skills

    fallback = []
    seen = set()
    for item in (student.student_skills or "").split(","):
        normalized = item.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        fallback.append({
            "name": normalized,
            "score": 50,
            "level": "beginner",
            "verified": False,
        })
    return fallback


def _student_focus_area(scores):
    focus_scores = {
        "Coding": scores.get("coding_skill_index", 0) or 0,
        "Communication": scores.get("communication_score", 0) or 0,
        "Authenticity": scores.get("authenticity_score", 0) or 0,
    }
    focus_area, _value = min(focus_scores.items(), key=lambda item: item[1])
    actions = {
        "Coding": "Schedule a coding round and review GitHub depth.",
        "Communication": "Assess storytelling, clarity, and mock interview confidence.",
        "Authenticity": "Review platform evidence and ask for project walkthroughs.",
    }
    return focus_area, actions[focus_area]


def _student_status_label(placement_ready, profile_verified):
    if placement_ready >= 80 and profile_verified:
        return "Interview ready"
    if placement_ready >= 70:
        return "Shortlist next"
    if placement_ready >= 55:
        return "Needs one more review"
    return "Needs coaching"


def _latest_resume_document(student):
    prefetched_documents = getattr(student, "_prefetched_objects_cache", {}).get("documents")
    if prefetched_documents is not None:
        for document in prefetched_documents:
            if document.doc_type == "resume" and document.file:
                return document
        return None
    return student.documents.filter(doc_type="resume").first()


def _resume_document_payload(document, download_path):
    if not document or not document.file:
        return None
    return {
        "filename": document.title or os.path.basename(document.file.name or "resume"),
        "uploaded_at": document.created_at.isoformat() if document.created_at else None,
        "download_path": download_path,
    }


def _resume_file_response(document):
    if not document or not document.file:
        return Response({'error': 'Resume not found'}, status=404)
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.title or os.path.basename(document.file.name or "resume"),
    )


def _build_skill_evidence_items(user, skill):
    items = []
    skill_name = (skill.name or "").strip()
    skill_name_lower = skill_name.lower()
    resume_document = _latest_resume_document(user)
    student_skills_text = (user.student_skills or "").lower()

    if resume_document:
        items.append({
            "source": "resume",
            "title": "Resume evidence",
            "detail": f"Referenced in uploaded resume: {resume_document.title}",
            "url": "/api/skills/resume/",
            "created_at": resume_document.created_at.isoformat() if resume_document.created_at else None,
        })

    if skill_name_lower and skill_name_lower in student_skills_text:
        items.append({
            "source": "profile",
            "title": "Declared by student",
            "detail": "Listed in the student skill profile.",
            "url": "/dashboard/settings",
            "created_at": None,
        })

    latest_report = user.code_analysis_reports.filter(status="completed").first()
    if latest_report:
        items.append({
            "source": "repository",
            "title": "Repository analysis",
            "detail": latest_report.repo_url,
            "url": latest_report.repo_url,
            "created_at": latest_report.created_at.isoformat() if latest_report.created_at else None,
        })

    latest_submission = user.submissions.exclude(repo_url="").first()
    if latest_submission:
        items.append({
            "source": "project",
            "title": latest_submission.title or "Project submission",
            "detail": latest_submission.repo_url or (latest_submission.description or "Project evidence"),
            "url": latest_submission.repo_url,
            "created_at": latest_submission.created_at.isoformat() if latest_submission.created_at else None,
        })

    interview_session = user.ai_interviews.filter(status="completed").first()
    if interview_session:
        items.append({
            "source": "interview",
            "title": "Interview verification",
            "detail": f"Completed AI interview with score {_interview_state_payload(interview_session)['score']}/100.",
            "url": "/dashboard/interview",
            "created_at": interview_session.completed_at.isoformat() if interview_session.completed_at else None,
        })

    media_upload = user.media_uploads.exclude(status="processing").first()
    if media_upload:
        items.append({
            "source": media_upload.media_type,
            "title": media_upload.title,
            "detail": f"{media_upload.media_type.title()} upload available as supporting evidence.",
            "url": "/dashboard/media",
            "created_at": media_upload.created_at.isoformat() if media_upload.created_at else None,
        })

    public_links = [
        ("GitHub", user.github_link),
        ("LeetCode", user.leetcode_link),
        ("LinkedIn", user.linkedin_link),
        ("CodeChef", user.codechef_link),
        ("HackerRank", user.hackerrank_link),
    ]
    for label, url in public_links:
        if not url:
            continue
        items.append({
            "source": label.lower(),
            "title": f"{label} profile connected",
            "detail": url,
            "url": url,
            "created_at": None,
        })
        if len(items) >= 6:
            break

    deduped = []
    seen = set()
    for item in items:
        key = (item["source"], item["title"], item["detail"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:6]


def _resume_preview_payload(user):
    skills = list(user.skills.order_by('-verified', '-score', 'name')[:10])
    scorecards = list(user.scorecards.all())
    latest_interview = user.ai_interviews.filter(status='completed').first()
    latest_report = user.code_analysis_reports.filter(status='completed').first()
    links = [
        {"label": "GitHub", "url": user.github_link},
        {"label": "LeetCode", "url": user.leetcode_link},
        {"label": "LinkedIn", "url": user.linkedin_link},
        {"label": "CodeChef", "url": user.codechef_link},
        {"label": "HackerRank", "url": user.hackerrank_link},
        {"label": "Codeforces", "url": user.codeforces_link},
        {"label": "GeeksforGeeks", "url": user.gfg_link},
    ]

    top_skill_names = [skill.name for skill in skills[:4] if skill.name]
    summary = (
        user.linkedin_about
        or user.linkedin_headline
        or (
            f"{user.full_name or user.username} is a {user.course or 'student'} focused on "
            f"{', '.join(top_skill_names) or 'applied software projects'} with a placement readiness "
            f"score of {next((card.score for card in scorecards if card.score_type == 'placement_ready'), 0)}/100."
        )
    )

    achievements = []
    for card in scorecards:
        label = card.score_type.replace('_', ' ').title()
        achievements.append(f"{label}: {card.score}/100")
    if latest_interview:
        achievements.append(
            f"AI interview score: {_interview_state_payload(latest_interview)['score']}/100"
        )
    if latest_report:
        achievements.append(f"Repository analyzed: {latest_report.repo_url}")

    return {
        "full_name": user.full_name or user.username,
        "headline": user.linkedin_headline or "Verified student profile",
        "summary": summary,
        "education": {
            "college": user.college or "",
            "course": user.course or "",
            "branch": user.branch or "",
            "year_of_study": user.year_of_study or "",
            "cgpa": float(user.cgpa) if user.cgpa is not None else None,
        },
        "skills": [
            {
                "name": skill.name,
                "level": skill.level,
                "score": skill.score,
                "verified": skill.verified,
            }
            for skill in skills
        ],
        "achievements": achievements[:6],
        "projects": [
            {
                "title": report.repo_url if report.repo_url else "Repository analysis",
                "description": report.summary or "AI-analyzed code repository.",
                "link": report.repo_url,
            }
            for report in user.code_analysis_reports.filter(status='completed')[:3]
        ] + [
            {
                "title": submission.title,
                "description": submission.description or "Project submission",
                "link": submission.repo_url,
            }
            for submission in user.submissions.exclude(repo_url='')[:2]
        ],
        "links": [item for item in links if item["url"]],
    }


def _interview_history_payload(user, limit=6):
    sessions = user.ai_interviews.all()[:limit]
    payload = []
    for session in sessions:
        answers = session.answers or []
        summary = _build_interview_summary(answers) if answers else {"strengths": [], "improvements": []}
        payload.append({
            "id": session.id,
            "status": session.status,
            "score": _interview_state_payload(session)["score"],
            "answered": len(answers),
            "questions": len(session.questions or []),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "strengths": summary.get("strengths", [])[:2],
            "improvements": summary.get("improvements", [])[:2],
        })
    return payload


def _student_summary_payload(student):
    scores = _student_score_map(student)
    skills = _student_skill_payload(student)
    resume_document = _latest_resume_document(student)
    placement_ready = int(scores.get("placement_ready", 0) or 0)
    focus_area, recommended_action = _student_focus_area(scores)
    top_skills = skills[:8]
    profile_verified = bool(student.profile_verified)

    return {
        "id": student.id,
        "verification_id": f"SKV-{student.id:05d}",
        "name": student.full_name or student.username,
        "email": student.email,
        "college": student.college or "",
        "course": student.course or "Student",
        "branch": student.branch or "",
        "year_of_study": student.year_of_study or "",
        "cgpa": float(student.cgpa) if student.cgpa is not None else None,
        "location": student.branch or "",
        "headline": student.linkedin_headline or "",
        "summary": student.linkedin_about or "",
        "profile_verified": profile_verified,
        "status_label": _student_status_label(placement_ready, profile_verified),
        "focus_area": focus_area,
        "recommended_action": recommended_action,
        "needs_attention": placement_ready < 60 or not profile_verified,
        "score": placement_ready,
        "scores": {
            "placement_ready": placement_ready,
            "coding_skill_index": int(scores.get("coding_skill_index", 0) or 0),
            "communication_score": int(scores.get("communication_score", 0) or 0),
            "authenticity_score": int(scores.get("authenticity_score", 0) or 0),
        },
        "skills": top_skills,
        "verified_skills": sum(1 for skill in top_skills if skill["verified"]),
        "highlights": [skill["name"] for skill in top_skills[:3]],
        "resume_document": _resume_document_payload(
            resume_document,
            f"/api/skills/recruiter-dashboard/resume/{student.id}/",
        ),
        "links": {
            "github": student.github_link or "",
            "leetcode": student.leetcode_link or "",
            "linkedin": student.linkedin_link or "",
            "codechef": student.codechef_link or "",
            "hackerrank": student.hackerrank_link or "",
            "codeforces": student.codeforces_link or "",
            "gfg": student.gfg_link or "",
        },
        "last_analyzed_at": student.last_analyzed_at.isoformat() if student.last_analyzed_at else None,
    }


def _skill_distribution_for_students(student_payloads, limit=8):
    counts = {}
    for payload in student_payloads:
        for skill in payload.get("skills", [])[:6]:
            name = skill.get("name")
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1
    items = sorted(
        [{"name": name, "count": count} for name, count in counts.items()],
        key=lambda item: (-item["count"], item["name"].lower()),
    )
    return items[:limit]


def _trend_for_students(student_ids, student_payloads):
    if not student_ids:
        return []

    cutoff = timezone.localdate() - timedelta(days=90)
    snapshots = ScoreSnapshot.objects.filter(
        user_id__in=student_ids,
        recorded_on__gte=cutoff,
    ).order_by("recorded_on")

    buckets = {}
    for snapshot in snapshots:
        bucket = buckets.setdefault(snapshot.recorded_on, {
            "count": 0,
            "placement_ready": 0,
            "coding_skill_index": 0,
            "communication_score": 0,
            "authenticity_score": 0,
        })
        bucket["count"] += 1
        scores = snapshot.scores or {}
        for field in ["placement_ready", "coding_skill_index", "communication_score", "authenticity_score"]:
            bucket[field] += scores.get(field, 0) or 0

    if not buckets:
        if not student_payloads:
            return []
        return [{
            "date": timezone.localdate().isoformat(),
            "placement_ready": _score_mean([item["scores"]["placement_ready"] for item in student_payloads]),
            "coding_skill_index": _score_mean([item["scores"]["coding_skill_index"] for item in student_payloads]),
            "communication_score": _score_mean([item["scores"]["communication_score"] for item in student_payloads]),
            "authenticity_score": _score_mean([item["scores"]["authenticity_score"] for item in student_payloads]),
        }]

    series = []
    for recorded_on in sorted(buckets):
        bucket = buckets[recorded_on]
        count = bucket["count"] or 1
        series.append({
            "date": recorded_on.isoformat(),
            "placement_ready": round(bucket["placement_ready"] / count, 1),
            "coding_skill_index": round(bucket["coding_skill_index"] / count, 1),
            "communication_score": round(bucket["communication_score"] / count, 1),
            "authenticity_score": round(bucket["authenticity_score"] / count, 1),
        })
    return series


def _interventions_for_students(student_payloads, limit=6):
    interventions = []
    for payload in student_payloads:
        reasons = []
        scores = payload["scores"]
        if payload["score"] < 60:
            reasons.append("Placement readiness is below 60.")
        if scores["coding_skill_index"] < 55:
            reasons.append("Coding evidence is still weak.")
        if scores["communication_score"] < 55:
            reasons.append("Communication needs more structure.")
        if not payload["profile_verified"]:
            reasons.append("Verification interview is incomplete.")
        if not reasons:
            continue
        severity = "high" if payload["score"] < 50 else "medium" if payload["score"] < 65 else "low"
        interventions.append({
            "id": payload["id"],
            "name": payload["name"],
            "verification_id": payload["verification_id"],
            "college": payload["college"],
            "branch": payload["branch"],
            "score": payload["score"],
            "focus_area": payload["focus_area"],
            "severity": severity,
            "reason": " ".join(reasons[:2]),
            "action": payload["recommended_action"],
        })
    interventions.sort(key=lambda item: (item["score"], item["name"].lower()))
    return interventions[:limit]

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
    verified = []
    for skill in skills.filter(verified=True):
        evidence_items = _build_skill_evidence_items(request.user, skill)
        verified.append(
            {
                'name': skill.name,
                'level': skill.level,
                'evidence': len(evidence_items),
                'verified': skill.verified,
                'evidence_items': evidence_items,
            }
        )
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
            'history': _interview_history_payload(request.user),
            **_interview_state_payload(AIInterviewSession(user=request.user)),
        })
    return Response({
        'status': session.status,
        'transcript': session.transcript,
        'feedback': session.feedback,
        'metrics': session.metrics,
        'tips': session.tips,
        'history': _interview_history_payload(request.user),
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
            'history': _interview_history_payload(request.user),
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
            _create_notification(
                request.user,
                "Interview session completed",
                "Your mock interview history and latest score are now available.",
                category="verification" if request.user.profile_verified else "student",
                link="/dashboard/interview",
                metadata={"session_id": session.id, "score": _interview_state_payload(session)["score"]},
            )

        return Response({
            'status': session.status,
            'transcript': session.transcript,
            'feedback': session.feedback,
            'metrics': session.metrics,
            'tips': session.tips,
            'history': _interview_history_payload(request.user),
            **_interview_state_payload(session),
        })

    if action == 'finish':
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at', 'updated_at'])
        _maybe_mark_profile_verified(request.user, session)
        _create_notification(
            request.user,
            "Interview session ended",
            "Review coach notes and use the history panel to compare attempts.",
            category="student",
            link="/dashboard/interview",
            metadata={"session_id": session.id, "score": _interview_state_payload(session)["score"]},
        )
        return Response({
            'status': session.status,
            'history': _interview_history_payload(request.user),
            **_interview_state_payload(session),
        })

    return Response({'error': 'Invalid action'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recruiter_dashboard_view(request):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)
    _bootstrap_notifications_for_user(request.user)
    requested_job_id = _safe_int(request.query_params.get('job_id'), default=0)
    jobs = list(RecruiterJob.objects.filter(recruiter=request.user))
    selected_job = next((job for job in jobs if job.id == requested_job_id), None)
    if not selected_job and jobs:
        selected_job = next((job for job in jobs if job.status == 'open'), jobs[0])

    students = User.objects.filter(role='student').prefetch_related(
        'scorecards',
        'skills',
        'documents',
        'submissions',
        'ai_interviews',
        'code_analysis_reports',
    )
    pipeline_entries = list(
        RecruiterCandidatePipeline.objects.filter(recruiter=request.user).select_related('candidate', 'job')
    )
    pipeline_map = {
        (entry.candidate_id, entry.job_id): entry
        for entry in pipeline_entries
    }
    generic_pipeline_map = {
        entry.candidate_id: entry
        for entry in pipeline_entries
        if entry.job_id is None
    }

    candidates = []
    for student in students:
        payload = _student_summary_payload(student)
        match = _job_match_payload(payload, selected_job, student)
        pipeline_entry = (
            pipeline_map.get((student.id, selected_job.id if selected_job else None))
            if selected_job
            else generic_pipeline_map.get(student.id)
        )
        payload['match_score'] = (
            int(pipeline_entry.match_score or 0)
            if pipeline_entry and pipeline_entry.match_score
            else match['score']
        )
        payload['match_reasons'] = match['reasons']
        payload['matched_skills'] = match['matched_skills']
        payload['missing_skills'] = match['missing_skills']
        payload['semantic_score'] = match['semantic_score']
        payload['matched_keywords'] = match['matched_keywords']
        payload['missing_keywords'] = match['missing_keywords']
        payload['pipeline'] = _candidate_pipeline_payload(pipeline_entry)
        candidates.append(payload)

    sort_key = "match_score" if selected_job else "score"
    candidates = sorted(
        candidates,
        key=lambda item: (-item[sort_key], -item["score"], item["name"].lower()),
    )
    summary = {
        "candidates": len(candidates),
        "average_ready": _score_mean([item["score"] for item in candidates]),
        "verified_profiles": sum(1 for item in candidates if item["profile_verified"]),
        "shortlist_ready": sum(1 for item in candidates if item["score"] >= 75),
        "active_jobs": sum(1 for job in jobs if job.status == 'open'),
        "shortlisted": sum(1 for entry in pipeline_entries if entry.status == 'shortlisted'),
    }
    available_skills = sorted({
        skill["name"]
        for candidate in candidates
        for skill in candidate.get("skills", [])
        if skill.get("name")
    })
    job_payloads = []
    for job in jobs[:10]:
        top_matches = 0
        for candidate in candidates:
            if _job_match_payload(candidate, job, None)["score"] >= max(int(job.min_ready_score or 0), 60):
                top_matches += 1
        item = _job_payload(job)
        item["top_matches"] = top_matches
        job_payloads.append(item)

    schedules = InterviewSchedule.objects.filter(recruiter=request.user).select_related('candidate', 'job')[:12]

    return Response({
        'summary': summary,
        'filters': {
            'skills': available_skills[:20],
        },
        'selected_job_id': selected_job.id if selected_job else None,
        'jobs': job_payloads,
        'saved_searches': [
            _saved_search_payload(search)
            for search in RecruiterSavedSearch.objects.filter(recruiter=request.user)[:8]
        ],
        'pipeline_summary': _pipeline_summary_for_entries(pipeline_entries),
        'interview_schedules': [_interview_schedule_payload(schedule) for schedule in schedules],
        'candidates': candidates,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def recruiter_jobs_view(request):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        title = (request.data.get('title') or '').strip()
        if not title:
            return Response({'error': 'Job title is required'}, status=400)
        job = RecruiterJob.objects.create(
            recruiter=request.user,
            title=title,
            description=(request.data.get('description') or '').strip(),
            required_skills=_normalize_string_list(request.data.get('required_skills')),
            preferred_skills=_normalize_string_list(request.data.get('preferred_skills')),
            min_ready_score=_safe_int(request.data.get('min_ready_score'), default=60),
            status=(request.data.get('status') or 'open').strip() or 'open',
        )
        _create_notification(
            request.user,
            "Job brief saved",
            f"{job.title} is ready for candidate matching.",
            category="recruiter",
            link="/recruiter/dashboard",
            metadata={"job_id": job.id},
        )
        return Response({'job': _job_payload(job)}, status=201)

    return Response({
        'jobs': [_job_payload(job) for job in RecruiterJob.objects.filter(recruiter=request.user)],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recruiter_pipeline_view(request, candidate_id):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    candidate = User.objects.filter(role='student', id=candidate_id).prefetch_related(
        'scorecards',
        'skills',
        'documents',
    ).first()
    if not candidate:
        return Response({'error': 'Candidate not found'}, status=404)

    job = None
    job_id = _safe_int(request.data.get('job_id'), default=0)
    if job_id:
        job = RecruiterJob.objects.filter(recruiter=request.user, id=job_id).first()
        if not job:
            return Response({'error': 'Job not found'}, status=404)

    status_value = (request.data.get('status') or 'sourced').strip() or 'sourced'
    tags = _normalize_string_list(request.data.get('tags'))
    notes = (request.data.get('notes') or '').strip()
    assignee_name = (request.data.get('assignee_name') or '').strip()
    next_step = (request.data.get('next_step') or '').strip()
    rejection_reason = (request.data.get('rejection_reason') or '').strip()
    follow_up_raw = (request.data.get('follow_up_at') or '').strip()
    follow_up_at = None
    if follow_up_raw:
        try:
            follow_up_at = timezone.datetime.fromisoformat(follow_up_raw.replace("Z", "+00:00"))
            if timezone.is_naive(follow_up_at):
                follow_up_at = timezone.make_aware(follow_up_at, timezone.get_current_timezone())
        except (TypeError, ValueError):
            follow_up_at = None
    candidate_payload = _student_summary_payload(candidate)
    match = _job_match_payload(candidate_payload, job, candidate)
    pipeline_entry, _ = RecruiterCandidatePipeline.objects.update_or_create(
        recruiter=request.user,
        candidate=candidate,
        job=job,
        defaults={
            'status': status_value,
            'notes': notes,
            'tags': tags,
            'match_score': match['score'],
            'assignee_name': assignee_name,
            'next_step': next_step,
            'rejection_reason': rejection_reason,
            'follow_up_at': follow_up_at,
            'last_contacted_at': timezone.now() if request.data.get('contacted') else None,
        },
    )

    if status_value in {'shortlisted', 'interviewing', 'offered'}:
        _create_notification(
            candidate,
            "Recruiter activity",
            f"Your profile moved to {status_value.replace('_', ' ')} for {job.title if job else 'a recruiter review'}.",
            category="student",
            link="/dashboard",
            metadata={"job_id": job.id if job else None, "status": status_value},
        )

    return Response({
        'pipeline': _candidate_pipeline_payload(pipeline_entry),
        'match': match,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def interview_schedules_view(request):
    if request.method == 'POST':
        if not _require_role(request.user, 'recruiter'):
            return Response({'error': 'Unauthorized'}, status=403)
        candidate_id = _safe_int(request.data.get('candidate_id'), default=0)
        candidate = User.objects.filter(role='student', id=candidate_id).first()
        if not candidate:
            return Response({'error': 'Candidate not found'}, status=404)
        scheduled_at_raw = (request.data.get('scheduled_at') or '').strip()
        if not scheduled_at_raw:
            return Response({'error': 'Interview date and time are required'}, status=400)
        try:
            scheduled_at = timezone.datetime.fromisoformat(scheduled_at_raw.replace("Z", "+00:00"))
            if timezone.is_naive(scheduled_at):
                scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
        except (TypeError, ValueError):
            return Response({'error': 'Invalid interview date format'}, status=400)

        job = None
        job_id = _safe_int(request.data.get('job_id'), default=0)
        if job_id:
            job = RecruiterJob.objects.filter(recruiter=request.user, id=job_id).first()
            if not job:
                return Response({'error': 'Job not found'}, status=404)

        schedule = InterviewSchedule.objects.create(
            recruiter=request.user,
            candidate=candidate,
            job=job,
            title=(request.data.get('title') or '').strip() or f"{job.title if job else 'Interview'} discussion",
            scheduled_at=scheduled_at,
            duration_minutes=max(15, _safe_int(request.data.get('duration_minutes'), default=30)),
            meeting_link=(request.data.get('meeting_link') or '').strip(),
            notes=(request.data.get('notes') or '').strip(),
        )
        _create_notification(
            candidate,
            "Interview scheduled",
            f"{request.user.full_name or request.user.username} scheduled an interview on {timezone.localtime(schedule.scheduled_at).strftime('%b %d, %Y %I:%M %p')}.",
            category="student",
            link="/dashboard",
            metadata={"schedule_id": schedule.id, "job_id": schedule.job_id},
        )
        return Response({'schedule': _interview_schedule_payload(schedule)}, status=201)

    if _require_role(request.user, 'recruiter'):
        schedules = InterviewSchedule.objects.filter(recruiter=request.user).select_related('candidate', 'job')[:20]
    elif _require_role(request.user, 'student'):
        schedules = InterviewSchedule.objects.filter(candidate=request.user).select_related('recruiter', 'job')[:20]
    else:
        return Response({'schedules': []})

    return Response({'schedules': [_interview_schedule_payload(schedule) for schedule in schedules]})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def recruiter_saved_searches_view(request):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'error': 'Search name is required'}, status=400)
        filters = request.data.get('filters') if isinstance(request.data.get('filters'), dict) else {}
        saved_search = RecruiterSavedSearch.objects.create(
            recruiter=request.user,
            name=name,
            query=(request.data.get('query') or '').strip(),
            filters=filters,
        )
        return Response({'saved_search': _saved_search_payload(saved_search)}, status=201)

    return Response({
        'saved_searches': [
            _saved_search_payload(search)
            for search in RecruiterSavedSearch.objects.filter(recruiter=request.user)
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recruiter_candidate_report_view(request, student_id):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    student = User.objects.filter(role='student', id=student_id).prefetch_related('scorecards', 'skills', 'documents').first()
    if not student:
        return Response({'error': 'Candidate not found'}, status=404)

    candidate = _student_summary_payload(student)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except ImportError:
        return Response({'error': 'PDF export requires the reportlab package.'}, status=500)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 0.75 * inch
    y = height - x_margin

    def draw_line(label, value, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_margin, y, f"{label}:")
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        pdf.drawString(x_margin + 1.45 * inch, y, value or "-")
        y -= 0.2 * inch

    def draw_wrapped(label, value):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_margin, y, f"{label}:")
        y -= 0.16 * inch
        pdf.setFont("Helvetica", 10)
        for line in textwrap.wrap(value or "-", width=88):
            pdf.drawString(x_margin + 0.2 * inch, y, line)
            y -= 0.16 * inch

    pdf.setTitle(f"{candidate['name']} - Candidate Summary")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(x_margin, y, "Recruiter Candidate Summary")
    y -= 0.3 * inch

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x_margin, y, candidate["name"])
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - x_margin, y, candidate["verification_id"])
    y -= 0.26 * inch

    draw_line("Email", candidate["email"])
    draw_line("College", candidate["college"] or "-")
    draw_line("Course", candidate["course"] or "-")
    draw_line("Branch", candidate["branch"] or "-")
    draw_line("Year", candidate["year_of_study"] or "-")
    draw_line("Placement Ready", f"{candidate['scores']['placement_ready']}/100", bold=True)
    draw_line("Coding Skill Index", f"{candidate['scores']['coding_skill_index']}/100")
    draw_line("Communication Score", f"{candidate['scores']['communication_score']}/100")
    draw_line("Authenticity Score", f"{candidate['scores']['authenticity_score']}/100")
    draw_line("Status", candidate["status_label"])
    draw_line("Focus Area", candidate["focus_area"])
    draw_line(
        "Resume",
        candidate["resume_document"]["filename"] if candidate["resume_document"] else "Not uploaded",
    )

    y -= 0.08 * inch
    draw_wrapped("Recommended Action", candidate["recommended_action"])
    draw_wrapped("Top Skills", ", ".join(skill["name"] for skill in candidate["skills"]) or "No skills available")

    links = [url for url in candidate["links"].values() if url]
    draw_wrapped("Portfolio Links", ", ".join(links) if links else "No public links connected")

    if candidate["summary"]:
        draw_wrapped("LinkedIn Summary", candidate["summary"])

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    filename = f"{candidate['name'].replace(' ', '_').lower()}-candidate-summary.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recruiter_candidate_resume_view(request, student_id):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    resume_document = Document.objects.filter(
        user_id=student_id,
        user__role='student',
        doc_type='resume',
    ).first()
    return _resume_file_response(resume_document)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resume_document_view(request):
    if not _require_role(request.user, 'student'):
        return Response({'error': 'Unauthorized'}, status=403)
    return _resume_file_response(_latest_resume_document(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resume_builder_view(request):
    if not _require_role(request.user, 'student'):
        return Response({'error': 'Unauthorized'}, status=403)
    preview = _resume_preview_payload(request.user)
    preview["generated_at"] = timezone.now().isoformat()
    return Response(preview)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resume_builder_pdf_view(request):
    if not _require_role(request.user, 'student'):
        return Response({'error': 'Unauthorized'}, status=403)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except ImportError:
        return Response({'error': 'PDF export requires the reportlab package.'}, status=500)

    preview = _resume_preview_payload(request.user)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 0.75 * inch
    y = height - margin

    def draw_heading(text):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(margin, y, text)
        y -= 0.22 * inch

    def draw_body(lines, indent=0.0):
        nonlocal y
        pdf.setFont("Helvetica", 10)
        for line in lines:
            for wrapped in textwrap.wrap(line or "-", width=92):
                pdf.drawString(margin + indent, y, wrapped)
                y -= 0.16 * inch
                if y < margin:
                    pdf.showPage()
                    y = height - margin
                    pdf.setFont("Helvetica", 10)

    pdf.setTitle(f"{preview['full_name']} - Resume")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, y, preview["full_name"])
    y -= 0.22 * inch
    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, y, preview["headline"])
    y -= 0.3 * inch

    draw_heading("Professional Summary")
    draw_body([preview["summary"]])
    y -= 0.08 * inch

    education = preview["education"]
    draw_heading("Education")
    education_lines = [
        " | ".join(
            [
                value
                for value in [
                    education.get("college"),
                    education.get("course"),
                    education.get("branch"),
                    education.get("year_of_study"),
                ]
                if value
            ]
        ) or "Education details pending",
    ]
    if education.get("cgpa") is not None:
        education_lines.append(f"CGPA: {education['cgpa']}")
    draw_body(education_lines)
    y -= 0.08 * inch

    draw_heading("Skills")
    draw_body([
        ", ".join(
            f"{item['name']} ({item['level']}, {item['score']}/100)"
            for item in preview["skills"]
        ) or "No verified skills yet"
    ])
    y -= 0.08 * inch

    draw_heading("Projects")
    project_lines = []
    for project in preview["projects"][:5]:
        project_lines.append(f"{project['title']}: {project['description']}")
    draw_body(project_lines or ["No project evidence available yet"])
    y -= 0.08 * inch

    draw_heading("Highlights")
    draw_body(preview["achievements"] or ["No score highlights available yet"])
    y -= 0.08 * inch

    draw_heading("Links")
    draw_body([f"{item['label']}: {item['url']}" for item in preview["links"]] or ["No public links connected"])

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    _create_notification(
        request.user,
        "Resume generated",
        "Your ATS-ready resume export is ready for download.",
        category="student",
        link="/dashboard/resume-builder",
    )

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="skillsense-resume.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_view(request):
    _bootstrap_notifications_for_user(request.user)
    notifications = Notification.objects.filter(user=request.user)[:12]
    return Response({
        "unread_count": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
        "notifications": [_notification_payload(notification) for notification in notifications],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_read_view(request, notification_id):
    queryset = Notification.objects.filter(user=request.user)
    if notification_id == 0:
        queryset.filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"message": "All notifications marked as read"})

    notification = queryset.filter(id=notification_id).first()
    if not notification:
        return Response({'error': 'Notification not found'}, status=404)
    if not notification.read_at:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at'])
    return Response({"notification": _notification_payload(notification)})


def _batch_row_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _coerce_csv_bool(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _ingest_batch_row(university, row):
    email = _batch_row_value(row, "email", "Email")
    if not email:
        return "skipped", None

    full_name = _batch_row_value(row, "full_name", "name", "Name")
    username = email.split("@")[0] or (full_name.replace(" ", "").lower() if full_name else email)
    defaults = {
        "username": username[:150],
        "role": "student",
    }
    student, created = User.objects.get_or_create(email=email, defaults=defaults)
    if created:
        student.set_unusable_password()

    student.username = student.username or username[:150]
    student.role = "student"
    student.full_name = full_name or student.full_name
    student.college = _batch_row_value(row, "college", "College") or student.college
    student.course = _batch_row_value(row, "course", "Course") or student.course
    student.branch = _batch_row_value(row, "branch", "Branch") or student.branch
    student.year_of_study = _batch_row_value(row, "year_of_study", "year", "Year") or student.year_of_study
    cgpa_value = _batch_row_value(row, "cgpa", "CGPA")
    if cgpa_value:
        try:
            student.cgpa = float(cgpa_value)
        except (TypeError, ValueError):
            pass
    student.student_skills = _batch_row_value(row, "student_skills", "skills", "Skills") or student.student_skills
    verified_value = _batch_row_value(row, "profile_verified", "verified")
    if verified_value:
        student.profile_verified = _coerce_csv_bool(verified_value)
    student.save()

    score_map = {
        "placement_ready": _safe_int(_batch_row_value(row, "placement_ready", "ready_score")),
        "coding_skill_index": _safe_int(_batch_row_value(row, "coding_skill_index", "coding_score")),
        "communication_score": _safe_int(_batch_row_value(row, "communication_score", "communication")),
        "authenticity_score": _safe_int(_batch_row_value(row, "authenticity_score", "authenticity")),
    }
    if any(score_map.values()):
        for score_type, score in score_map.items():
            ScoreCard.objects.update_or_create(
                user=student,
                score_type=score_type,
                defaults={"score": score, "change": 0},
            )
        ScoreSnapshot.objects.update_or_create(
            user=student,
            recorded_on=timezone.localdate(),
            defaults={"scores": score_map},
        )

    imported_skills = _normalize_string_list(_batch_row_value(row, "student_skills", "skills", "Skills"))
    verified_skills = {
        item.lower()
        for item in _normalize_string_list(_batch_row_value(row, "verified_skills", "Verified Skills"))
    }
    coding_score = score_map["coding_skill_index"]
    inferred_level = (
        "advanced" if coding_score >= 75 else "intermediate" if coding_score >= 55 else "beginner"
    )
    inferred_score = coding_score or max(score_map["placement_ready"], 50)
    for skill_name in imported_skills[:15]:
        Skill.objects.update_or_create(
            user=student,
            name=skill_name,
            defaults={
                "level": inferred_level,
                "score": inferred_score,
                "verified": student.profile_verified or skill_name.lower() in verified_skills,
            },
        )

    _create_notification(
        student,
        "University profile synced",
        f"{university.full_name or university.username} updated your cohort profile data.",
        category="student",
        link="/dashboard",
        metadata={"source": "batch_upload"},
    )
    return ("created" if created else "updated"), student


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def university_dashboard_view(request):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)
    _bootstrap_notifications_for_user(request.user)
    branch = (request.query_params.get('branch') or '').strip()
    course = (request.query_params.get('course') or '').strip()
    year_of_study = (request.query_params.get('year_of_study') or '').strip()

    students = User.objects.filter(role='student')
    if branch:
        students = students.filter(branch=branch)
    if course:
        students = students.filter(course=course)
    if year_of_study:
        students = students.filter(year_of_study=year_of_study)

    students = students.prefetch_related('scorecards', 'skills', 'documents')
    student_payloads = sorted(
        [_student_summary_payload(student) for student in students],
        key=lambda item: (-item["score"], item["name"].lower()),
    )
    totals = len(student_payloads)
    placement_scores = [student["scores"]["placement_ready"] for student in student_payloads]
    coding_scores = [student["scores"]["coding_skill_index"] for student in student_payloads]
    authenticity_scores = [student["scores"]["authenticity_score"] for student in student_payloads]
    verified_profiles = sum(1 for student in student_payloads if student["profile_verified"])
    need_attention = sum(1 for student in student_payloads if student["needs_attention"])
    student_ids = [student["id"] for student in student_payloads]
    all_students = User.objects.filter(role='student')
    intervention_map = {
        record.student_id: record
        for record in InterventionRecord.objects.filter(
            university=request.user,
            student_id__in=student_ids,
        )
    }
    interventions = []
    for item in _interventions_for_students(student_payloads):
        record = intervention_map.get(item["id"])
        item["status"] = record.status if record else "planned"
        item["priority"] = record.priority if record else item["severity"]
        item["note"] = record.note if record else ""
        item["recommended_action"] = record.recommended_action if record and record.recommended_action else item["action"]
        item["record"] = _intervention_record_payload(record)
        interventions.append(item)
    drives = [
        _placement_drive_payload(drive, student_payloads)
        for drive in PlacementDrive.objects.filter(university=request.user)[:8]
    ]
    return Response({
        'summary': {
            'students': totals,
            'average_ready': _score_mean(placement_scores),
            'average_coding': _score_mean(coding_scores),
            'average_authenticity': _score_mean(authenticity_scores),
            'verified_profiles': verified_profiles,
            'need_attention': need_attention,
            'tracked_interventions': sum(
                1 for record in intervention_map.values() if record.status != 'completed'
            ),
        },
        'filters': {
            'branches': sorted(filter(None, all_students.values_list('branch', flat=True).distinct())),
            'courses': sorted(filter(None, all_students.values_list('course', flat=True).distinct())),
            'years': sorted(filter(None, all_students.values_list('year_of_study', flat=True).distinct())),
        },
        'readiness_breakdown': [
            {'name': 'Ready', 'count': sum(1 for item in student_payloads if item['score'] >= 75)},
            {'name': 'Almost Ready', 'count': sum(1 for item in student_payloads if 60 <= item['score'] < 75)},
            {'name': 'Needs Support', 'count': sum(1 for item in student_payloads if item['score'] < 60)},
        ],
        'skill_distribution': _skill_distribution_for_students(student_payloads),
        'placement_trend': _trend_for_students(student_ids, student_payloads),
        'interventions': interventions,
        'top_students': student_payloads[:5],
        'students': student_payloads,
        'batch_uploads': [
            _batch_upload_payload(batch_upload)
            for batch_upload in UniversityBatchUpload.objects.filter(university=request.user)[:5]
        ],
        'placement_drives': drives,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def university_batch_upload_view(request):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)

    upload = request.FILES.get('file')
    if not upload:
        return Response({'error': 'CSV file is required'}, status=400)

    try:
        content = upload.read().decode('utf-8-sig')
    except Exception:
        return Response({'error': 'Unable to read CSV file'}, status=400)

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return Response({'error': 'CSV file must contain a header row'}, status=400)

    summary = {"created": 0, "updated": 0, "skipped": 0}
    with transaction.atomic():
        for row in reader:
            result, _student = _ingest_batch_row(request.user, row)
            if result in summary:
                summary[result] += 1
            else:
                summary["skipped"] += 1

        try:
            upload.seek(0)
        except Exception:
            pass
        batch_upload = UniversityBatchUpload.objects.create(
            university=request.user,
            filename=upload.name or "cohort.csv",
            file=upload,
            summary=summary,
            status='completed',
        )

    _create_notification(
        request.user,
        "Batch upload completed",
        f"Created {summary['created']} and updated {summary['updated']} student records.",
        category="university",
        link="/university/dashboard",
        metadata={"batch_upload_id": batch_upload.id, **summary},
    )
    return Response(
        {
            "batch_upload": _batch_upload_payload(batch_upload),
            "summary": summary,
        },
        status=201,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def university_intervention_view(request, student_id):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)

    student = User.objects.filter(role='student', id=student_id).first()
    if not student:
        return Response({'error': 'Student not found'}, status=404)

    status_value = (request.data.get('status') or 'planned').strip() or 'planned'
    priority = (request.data.get('priority') or 'medium').strip() or 'medium'
    note = (request.data.get('note') or '').strip()
    recommended_action = (request.data.get('recommended_action') or '').strip()

    record, _ = InterventionRecord.objects.update_or_create(
        university=request.user,
        student=student,
        defaults={
            'status': status_value,
            'priority': priority,
            'note': note,
            'recommended_action': recommended_action,
        },
    )
    _create_notification(
        student,
        "University support plan updated",
        f"Intervention status changed to {status_value.replace('_', ' ')}.",
        category="student",
        link="/dashboard/progress",
        metadata={"priority": priority},
    )
    return Response({'intervention': _intervention_record_payload(record)})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def university_placement_drives_view(request):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        company_name = (request.data.get('company_name') or '').strip()
        role_title = (request.data.get('role_title') or '').strip()
        if not company_name or not role_title:
            return Response({'error': 'Company name and role title are required'}, status=400)
        scheduled_on = None
        scheduled_on_raw = (request.data.get('scheduled_on') or '').strip()
        if scheduled_on_raw:
            try:
                scheduled_on = timezone.datetime.fromisoformat(scheduled_on_raw).date()
            except (TypeError, ValueError):
                scheduled_on = None
        drive = PlacementDrive.objects.create(
            university=request.user,
            company_name=company_name,
            role_title=role_title,
            description=(request.data.get('description') or '').strip(),
            target_branches=_normalize_string_list(request.data.get('target_branches')),
            target_courses=_normalize_string_list(request.data.get('target_courses')),
            minimum_ready_score=_safe_int(request.data.get('minimum_ready_score'), default=65),
            scheduled_on=scheduled_on,
            status=(request.data.get('status') or 'planning').strip() or 'planning',
        )
        students = [
            _student_summary_payload(student)
            for student in User.objects.filter(role='student').prefetch_related('scorecards', 'skills', 'documents')
        ]
        return Response({'drive': _placement_drive_payload(drive, students)}, status=201)

    students = [
        _student_summary_payload(student)
        for student in User.objects.filter(role='student').prefetch_related('scorecards', 'skills', 'documents')
    ]
    drives = [
        _placement_drive_payload(drive, students)
        for drive in PlacementDrive.objects.filter(university=request.user)
    ]
    return Response({'placement_drives': drives})




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
