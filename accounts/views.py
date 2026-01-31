import io
import os
import re
from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse
from django.utils import timezone
from .models import User as CustomUser
from .scoring import upsert_scorecards
from .scoring import analyze_platforms
from .scoring import score_breakdown

def _parse_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _maybe_int(field_name, value):
    if field_name in ['linkedin_experience_count', 'linkedin_skill_count', 'linkedin_cert_count']:
        return _parse_int(value)
    return value


def _extract_text_from_resume(uploaded_file):
    if not uploaded_file:
        return ""
    filename = (uploaded_file.name or "").lower()
    _, ext = os.path.splitext(filename)
    data = uploaded_file.read()
    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    if ext == ".pdf":
        try:
            from pdfminer.high_level import extract_text
        except ImportError:
            extract_text = None
        if extract_text:
            try:
                return extract_text(io.BytesIO(data))
            except Exception:
                return ""
        try:
            import PyPDF2
        except ImportError:
            PyPDF2 = None
        if PyPDF2:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(data))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                return ""
        return ""
    if ext == ".docx":
        try:
            import docx
        except ImportError:
            docx = None
        if not docx:
            return ""
        try:
            doc = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""
    if ext in {".txt", ".md", ".rtf"}:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return ""


def _clean_resume_text(text):
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _extract_first(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return match.group(1).strip() if match.groups() else match.group(0).strip()


def _extract_urls(text):
    url_pattern = r"(https?://[^\s)\]]+|www\.[^\s)\]]+|[a-z0-9.-]+\.[a-z]{2,}/[^\s)\]]+)"
    candidates = re.findall(url_pattern, text, flags=re.IGNORECASE)
    normalized = []
    for url in candidates:
        cleaned = url.rstrip(".,;)")
        if cleaned.startswith("www."):
            cleaned = "https://" + cleaned
        if not cleaned.startswith("http"):
            cleaned = "https://" + cleaned
        normalized.append(cleaned)
    return normalized


def _extract_skills(text):
    if not text:
        return []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    skills = []
    for idx, line in enumerate(lines):
        if re.search(r"\bskills?\b", line, flags=re.IGNORECASE):
            section = ""
            if ":" in line:
                section = line.split(":", 1)[1]
            else:
                section = ""
            lookahead = []
            for next_line in lines[idx + 1 : idx + 4]:
                if re.search(r"^[A-Z\s]{4,}$", next_line):
                    break
                if ":" in next_line and re.search(r"\bexperience|education|projects?\b", next_line, flags=re.IGNORECASE):
                    break
                lookahead.append(next_line)
            combined = " ".join([section] + lookahead)
            tokens = re.split(r"[,\|•;/]\s*", combined)
            for token in tokens:
                cleaned = token.strip(" .")
                if cleaned and len(cleaned) <= 40:
                    skills.append(cleaned)
            if skills:
                break
    seen = set()
    unique = []
    for skill in skills:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            unique.append(skill)
    return unique


def _extract_resume_fields(text):
    text = _clean_resume_text(text)
    fields = {}
    if not text:
        return fields

    fields["email"] = _extract_first(r"([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})", text)
    fields["phone_number"] = _extract_first(r"(\+?\d[\d\s\-()]{7,}\d)", text)

    urls = _extract_urls(text)
    for url in urls:
        lower = url.lower()
        if "github.com" in lower and not fields.get("github_link"):
            fields["github_link"] = url
        elif "leetcode.com" in lower and not fields.get("leetcode_link"):
            fields["leetcode_link"] = url
        elif "linkedin.com" in lower and not fields.get("linkedin_link"):
            fields["linkedin_link"] = url
        elif "codechef.com" in lower and not fields.get("codechef_link"):
            fields["codechef_link"] = url
        elif "hackerrank.com" in lower and not fields.get("hackerrank_link"):
            fields["hackerrank_link"] = url
        elif "codeforces.com" in lower and not fields.get("codeforces_link"):
            fields["codeforces_link"] = url
        elif "geeksforgeeks.org" in lower and not fields.get("gfg_link"):
            fields["gfg_link"] = url

    skills = _extract_skills(text)
    if skills:
        fields["student_skills"] = ", ".join(skills)

    fields["cgpa"] = _extract_first(r"\bCGPA[:\s]*([0-9]\.?[0-9]{0,2})", text)

    education_lines = [
        line.strip()
        for line in text.split("\n")
        if re.search(r"\b(university|college|institute|school)\b", line, flags=re.IGNORECASE)
    ]
    if education_lines and not fields.get("college"):
        fields["college"] = education_lines[0]

    degree_match = _extract_first(
        r"\b(B\.?Tech|B\.?E\.?|Bachelors?|M\.?Tech|M\.?E\.?|MCA|BCA|BSc|MSc|MBA)\b",
        text,
    )
    if degree_match:
        fields["course"] = degree_match

    branch_match = _extract_first(
        r"\b(Computer Science|Information Technology|Electronics|Electrical|Mechanical|Civil|Data Science|AI|Machine Learning|AI & ML|CSE|IT|ECE|EEE)\b",
        text,
    )
    if branch_match:
        fields["branch"] = branch_match

    return fields

@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    """
    Create a new user account
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    role = request.data.get('role', 'student')
    resume_file = request.FILES.get('resume') or request.data.get('resume')

    parsed_fields = _extract_resume_fields(_extract_text_from_resume(resume_file))

    # Student-specific fields
    full_name = request.data.get('full_name') or parsed_fields.get("full_name")
    gender = request.data.get('gender')
    phone_number = request.data.get('phone_number') or parsed_fields.get("phone_number")
    college = request.data.get('college') or parsed_fields.get("college")
    course = request.data.get('course') or parsed_fields.get("course")
    branch = request.data.get('branch') or parsed_fields.get("branch")
    year_of_study = request.data.get('year_of_study')
    cgpa = request.data.get('cgpa') or parsed_fields.get("cgpa")
    student_skills = request.data.get('student_skills') or parsed_fields.get("student_skills")
    github_link = request.data.get('github_link') or parsed_fields.get("github_link")
    leetcode_link = request.data.get('leetcode_link') or parsed_fields.get("leetcode_link")
    linkedin_link = request.data.get('linkedin_link') or parsed_fields.get("linkedin_link")
    linkedin_headline = request.data.get('linkedin_headline')
    linkedin_about = request.data.get('linkedin_about')
    linkedin_experience_count = _parse_int(request.data.get('linkedin_experience_count'))
    linkedin_skill_count = _parse_int(request.data.get('linkedin_skill_count'))
    linkedin_cert_count = _parse_int(request.data.get('linkedin_cert_count'))
    codechef_link = request.data.get('codechef_link') or parsed_fields.get("codechef_link")
    hackerrank_link = request.data.get('hackerrank_link') or parsed_fields.get("hackerrank_link")
    codeforces_link = request.data.get('codeforces_link') or parsed_fields.get("codeforces_link")
    gfg_link = request.data.get('gfg_link') or parsed_fields.get("gfg_link")

    email = email or parsed_fields.get("email")
    if not username:
        if email:
            username = email.split("@")[0]
        elif full_name:
            username = re.sub(r"\s+", "", full_name).lower()

    if not username or not email or not password:
        return Response(
            {'error': 'Username, email, and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if CustomUser.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if CustomUser.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            role=role,
            full_name=full_name,
            gender=gender,
            phone_number=phone_number,
            college=college,
            course=course,
            branch=branch,
            year_of_study=year_of_study,
            cgpa=cgpa,
            student_skills=student_skills,
            github_link=github_link,
            leetcode_link=leetcode_link,
            linkedin_link=linkedin_link,
            linkedin_headline=linkedin_headline,
            linkedin_about=linkedin_about,
            linkedin_experience_count=linkedin_experience_count,
            linkedin_skill_count=linkedin_skill_count,
            linkedin_cert_count=linkedin_cert_count,
            codechef_link=codechef_link,
            hackerrank_link=hackerrank_link,
            codeforces_link=codeforces_link,
            gfg_link=gfg_link
        )
        scores = upsert_scorecards(user) if user.role == 'student' else {}
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.full_name,
                'profile_verified': user.profile_verified,
                'gender': user.gender,
                'phone_number': user.phone_number,
                'college': user.college,
                'course': user.course,
                'branch': user.branch,
                'year_of_study': user.year_of_study,
                'cgpa': user.cgpa,
                'student_skills': user.student_skills,
                'github_link': user.github_link,
                'leetcode_link': user.leetcode_link,
                'linkedin_link': user.linkedin_link,
                'linkedin_headline': user.linkedin_headline,
                'linkedin_about': user.linkedin_about,
                'linkedin_experience_count': user.linkedin_experience_count,
                'linkedin_skill_count': user.linkedin_skill_count,
                'linkedin_cert_count': user.linkedin_cert_count,
                'codechef_link': user.codechef_link,
                'hackerrank_link': user.hackerrank_link,
                'codeforces_link': user.codeforces_link,
                'gfg_link': user.gfg_link,
            },
            'scores': scores
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {'error': 'Failed to create user'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and return JWT tokens
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = authenticate(username=email, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.full_name,
                'profile_verified': user.profile_verified,
            }
        })
        else:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
def logout_view(request):
    """
    Logout user by blacklisting refresh token
    """
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    user = request.user
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'full_name': user.full_name,
            'profile_verified': user.profile_verified,
            'gender': user.gender,
            'phone_number': user.phone_number,
            'college': user.college,
            'course': user.course,
            'branch': user.branch,
            'year_of_study': user.year_of_study,
            'cgpa': user.cgpa,
            'student_skills': user.student_skills,
            'github_link': user.github_link,
            'leetcode_link': user.leetcode_link,
            'linkedin_link': user.linkedin_link,
            'linkedin_headline': user.linkedin_headline,
            'linkedin_about': user.linkedin_about,
            'linkedin_experience_count': user.linkedin_experience_count,
            'linkedin_skill_count': user.linkedin_skill_count,
            'linkedin_cert_count': user.linkedin_cert_count,
            'codechef_link': user.codechef_link,
            'hackerrank_link': user.hackerrank_link,
            'codeforces_link': user.codeforces_link,
            'gfg_link': user.gfg_link,
            'linkedin_headline': user.linkedin_headline,
            'linkedin_about': user.linkedin_about,
            'linkedin_experience_count': user.linkedin_experience_count,
            'linkedin_skill_count': user.linkedin_skill_count,
            'linkedin_cert_count': user.linkedin_cert_count,
        }
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def profile_update_view(request):
    user = request.user
    fields = [
        'full_name', 'gender', 'phone_number', 'college', 'course', 'branch',
        'year_of_study', 'cgpa', 'student_skills', 'github_link', 'leetcode_link',
        'linkedin_link', 'codechef_link', 'hackerrank_link', 'codeforces_link',
        'gfg_link', 'linkedin_headline', 'linkedin_about',
        'linkedin_experience_count', 'linkedin_skill_count', 'linkedin_cert_count',
    ]
    for field in fields:
        if field in request.data:
            setattr(user, field, _maybe_int(field, request.data.get(field)))
    user.save()
    return profile_view(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    user = request.user
    scores = upsert_scorecards(user) if user.role == 'student' else {}
    github_stats = user.github_stats or {}
    github_repos = github_stats.get('repos', {}) if isinstance(github_stats, dict) else {}
    github_insights = {
        'top_languages': github_repos.get('top_languages', []),
        'forked': github_repos.get('forked', 0),
        'original': github_repos.get('original', 0),
        'fork_ratio': github_repos.get('fork_ratio', 0),
    }
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'email': user.email,
            'role': user.role,
            'profile_verified': user.profile_verified,
        },
        'scores': scores,
        'breakdown': score_breakdown(user) if user.role == 'student' else {},
        'github_insights': github_insights,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recalculate_scores_view(request):
    user = request.user
    if user.role != 'student':
        return Response({'scores': {}, 'breakdown': {}})
    analyze_platforms(user, force=True)
    scores = upsert_scorecards(user)
    github_stats = user.github_stats or {}
    github_repos = github_stats.get('repos', {}) if isinstance(github_stats, dict) else {}
    github_insights = {
        'top_languages': github_repos.get('top_languages', []),
        'forked': github_repos.get('forked', 0),
        'original': github_repos.get('original', 0),
        'fork_ratio': github_repos.get('fork_ratio', 0),
    }
    return Response({'scores': scores, 'breakdown': score_breakdown(user), 'github_insights': github_insights})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def score_report_view(request):
    user = request.user
    if user.role != 'student':
        return Response({'error': 'Score reports are available for students only.'}, status=403)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return Response(
            {'error': 'PDF export requires the reportlab package.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        matplotlib_available = True
    except Exception:
        matplotlib_available = False

    scores = upsert_scorecards(user)
    breakdown = score_breakdown(user)
    cutoff = timezone.localdate() - timedelta(days=90)
    series = list(user.score_snapshots.filter(recorded_on__gte=cutoff).order_by("recorded_on"))

    def render_chart(fig):
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
        if matplotlib_available:
            plt.close(fig)
        buffer.seek(0)
        return buffer

    def chart_scores_bar():
        if not matplotlib_available:
            return None
        labels = ["Coding", "Communication", "Authenticity", "Placement"]
        values = [
            scores.get("coding_skill_index", 0),
            scores.get("communication_score", 0),
            scores.get("authenticity_score", 0),
            scores.get("placement_ready", 0),
        ]
        fig, ax = plt.subplots(figsize=(6, 2.4))
        ax.barh(labels, values, color=["#2563eb", "#10b981", "#f59e0b", "#0ea5e9"])
        ax.set_xlim(0, 100)
        ax.set_title("Score Summary")
        for idx, value in enumerate(values):
            ax.text(value + 1, idx, str(value), va="center", fontsize=8)
        ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        return render_chart(fig)

    def chart_trend():
        if not matplotlib_available:
            return None
        if not series:
            return None
        dates = [snap.recorded_on for snap in series]
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.plot(dates, [snap.scores.get("coding_skill_index", 0) for snap in series], label="Coding", color="#2563eb")
        ax.plot(dates, [snap.scores.get("communication_score", 0) for snap in series], label="Communication", color="#10b981")
        ax.plot(dates, [snap.scores.get("authenticity_score", 0) for snap in series], label="Authenticity", color="#f59e0b")
        ax.plot(dates, [snap.scores.get("placement_ready", 0) for snap in series], label="Placement", color="#0ea5e9")
        ax.set_ylim(0, 100)
        ax.set_title("90 Day Trend")
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=6, ncol=2, loc="upper left")
        ax.spines[["top", "right"]].set_visible(False)
        return render_chart(fig)

    def chart_coding_mix():
        if not matplotlib_available:
            return None
        coding = breakdown.get("coding_skill_index", {})
        mix = {
            "LeetCode": coding.get("leetcode_solved_points", 0)
            + coding.get("leetcode_medium_points", 0)
            + coding.get("leetcode_hard_points", 0),
            "GitHub": coding.get("github_repos", 0) + coding.get("github_recent", 0) + coding.get("github_stars", 0),
            "Languages": coding.get("language_match", 0),
            "LeetCode Star": coding.get("leetcode_star", 0),
        }
        fig, ax = plt.subplots(figsize=(3.5, 2.4))
        ax.pie(list(mix.values()), labels=list(mix.keys()), autopct="%1.0f%%", textprops={"fontsize": 7})
        ax.set_title("Coding Mix")
        return render_chart(fig)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 0.75 * inch
    y = height - x_margin

    pdf.setTitle("SkillVerify Score Report")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(x_margin, y, "SkillVerify Score Report")
    y -= 0.3 * inch

    pdf.setFont("Helvetica", 10)
    generated_at = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M")
    pdf.drawString(x_margin, y, f"Generated: {generated_at}")
    y -= 0.25 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_margin, y, "Student Profile")
    y -= 0.2 * inch

    pdf.setFont("Helvetica", 10)
    profile_lines = [
        f"Name: {user.full_name or user.username}",
        f"Email: {user.email}",
        f"College: {user.college or '-'}",
        f"Course: {user.course or '-'}",
        f"Branch: {user.branch or '-'}",
        f"Year: {user.year_of_study or '-'}",
    ]
    for line in profile_lines:
        pdf.drawString(x_margin, y, line)
        y -= 0.18 * inch

    y -= 0.1 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_margin, y, "Score Summary")
    y -= 0.2 * inch
    pdf.setFont("Helvetica", 10)
    for key, value in scores.items():
        label = key.replace("_", " ").title()
        pdf.drawString(x_margin, y, f"{label}: {int(value)}")
        y -= 0.18 * inch

    if breakdown:
        y -= 0.1 * inch
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x_margin, y, "Score Breakdown")
        y -= 0.2 * inch
        pdf.setFont("Helvetica", 9)
        for category, parts in breakdown.items():
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(x_margin, y, category.replace("_", " ").title())
            y -= 0.18 * inch
            pdf.setFont("Helvetica", 9)
            for label, part_value in parts.items():
                pdf.drawString(x_margin + 0.2 * inch, y, f"{label.replace('_', ' ')}: {round(part_value, 1)}")
                y -= 0.16 * inch
            y -= 0.08 * inch

            if y < 1.2 * inch:
                pdf.showPage()
                y = height - x_margin
                pdf.setFont("Helvetica", 9)

    y -= 0.2 * inch
    if y < 3.5 * inch:
        pdf.showPage()
        y = height - x_margin

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_margin, y, "Analytics")
    y -= 0.2 * inch

    bar_chart = chart_scores_bar()
    if bar_chart:
        pdf.drawImage(ImageReader(bar_chart), x_margin, y - 2.4 * inch, width=6.5 * inch, height=2.4 * inch)
        y -= 2.7 * inch
    else:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x_margin, y, "Charts unavailable (matplotlib not installed).")
        y -= 0.3 * inch

    trend_chart = chart_trend()
    if trend_chart:
        pdf.drawImage(ImageReader(trend_chart), x_margin, y - 2.2 * inch, width=6.5 * inch, height=2.2 * inch)
        y -= 2.4 * inch

    mix_chart = chart_coding_mix()
    if mix_chart and y > 2.6 * inch:
        pdf.drawImage(ImageReader(mix_chart), x_margin, y - 2.4 * inch, width=3.5 * inch, height=2.4 * inch)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="skillverify-score-report.pdf"'
    return response
