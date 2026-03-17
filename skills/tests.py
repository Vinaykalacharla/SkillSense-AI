from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User
from .models import (
    AIInterviewSession,
    CodeAnalysisReport,
    Document,
    InterviewSchedule,
    InterventionRecord,
    PlacementDrive,
    RecruiterCandidatePipeline,
    RecruiterJob,
    ScoreCard,
    ScoreSnapshot,
    Skill,
    VerificationStep,
)


class RecruiterUniversityDashboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.recruiter = User.objects.create_user(
            username="recruiter",
            email="recruiter@example.com",
            password="password123",
            role="recruiter",
        )
        self.university = User.objects.create_user(
            username="university",
            email="university@example.com",
            password="password123",
            role="university",
        )

        self.student_one = User.objects.create_user(
            username="studentone",
            email="student1@example.com",
            password="password123",
            role="student",
            full_name="Student One",
            college="SkillSense University",
            course="B.Tech",
            branch="CSE",
            year_of_study="3rd Year",
            profile_verified=True,
            github_link="https://github.com/studentone",
            linkedin_link="https://linkedin.com/in/studentone",
        )
        self.student_two = User.objects.create_user(
            username="studenttwo",
            email="student2@example.com",
            password="password123",
            role="student",
            full_name="Student Two",
            college="SkillSense University",
            course="B.Tech",
            branch="ECE",
            year_of_study="4th Year",
            profile_verified=False,
            github_link="https://github.com/studenttwo",
        )

        self._add_student_metrics(
            self.student_one,
            placement_ready=82,
            coding_skill_index=78,
            communication_score=70,
            authenticity_score=76,
            skills=[
                ("Python", 84, "advanced", True),
                ("Django", 79, "advanced", True),
            ],
        )
        self._add_student_metrics(
            self.student_two,
            placement_ready=54,
            coding_skill_index=48,
            communication_score=52,
            authenticity_score=46,
            skills=[
                ("Java", 58, "intermediate", False),
                ("DSA", 50, "beginner", False),
            ],
        )
        Document.objects.create(
            user=self.student_one,
            title="student-one-resume.pdf",
            doc_type="resume",
            file=SimpleUploadedFile(
                "student-one-resume.pdf",
                b"%PDF-1.4 recruiter resume test",
                content_type="application/pdf",
            ),
            status="uploaded",
        )

    def _add_student_metrics(
        self,
        student,
        placement_ready,
        coding_skill_index,
        communication_score,
        authenticity_score,
        skills,
    ):
        for score_type, score in {
            "placement_ready": placement_ready,
            "coding_skill_index": coding_skill_index,
            "communication_score": communication_score,
            "authenticity_score": authenticity_score,
        }.items():
            ScoreCard.objects.create(user=student, score_type=score_type, score=score, change=0)

        for name, score, level, verified in skills:
            Skill.objects.create(
                user=student,
                name=name,
                score=score,
                level=level,
                verified=verified,
            )

        ScoreSnapshot.objects.create(
            user=student,
            recorded_on=timezone.localdate(),
            scores={
                "placement_ready": placement_ready,
                "coding_skill_index": coding_skill_index,
                "communication_score": communication_score,
                "authenticity_score": authenticity_score,
            },
        )

    def test_recruiter_dashboard_returns_candidates_and_summary(self):
        self.client.force_authenticate(user=self.recruiter)

        response = self.client.get("/api/skills/recruiter-dashboard/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["candidates"], 2)
        self.assertEqual(payload["summary"]["shortlist_ready"], 1)
        self.assertIn("skills", payload["filters"])
        self.assertEqual(payload["candidates"][0]["name"], "Student One")
        self.assertEqual(payload["candidates"][0]["scores"]["placement_ready"], 82)
        self.assertEqual(payload["candidates"][1]["focus_area"], "Authenticity")
        self.assertEqual(payload["candidates"][0]["resume_document"]["filename"], "student-one-resume.pdf")

    def test_recruiter_candidate_report_exports_pdf(self):
        self.client.force_authenticate(user=self.recruiter)

        response = self.client.get(f"/api/skills/recruiter-dashboard/report/{self.student_one.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("candidate-summary", response["Content-Disposition"])

    def test_recruiter_candidate_resume_downloads_uploaded_file(self):
        self.client.force_authenticate(user=self.recruiter)

        response = self.client.get(f"/api/skills/recruiter-dashboard/resume/{self.student_one.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("student-one-resume.pdf", response["Content-Disposition"])

    def test_university_dashboard_returns_filtered_analytics(self):
        self.client.force_authenticate(user=self.university)

        response = self.client.get("/api/skills/university-dashboard/?branch=CSE")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["students"], 1)
        self.assertEqual(payload["summary"]["average_ready"], 82.0)
        self.assertEqual(payload["readiness_breakdown"][0]["name"], "Ready")
        self.assertEqual(len(payload["placement_trend"]), 1)
        self.assertEqual(payload["students"][0]["branch"], "CSE")

    def test_recruiter_can_create_job_and_update_pipeline(self):
        self.client.force_authenticate(user=self.recruiter)

        create_response = self.client.post(
            "/api/skills/recruiter-dashboard/jobs/",
            {
                "title": "Backend Engineer",
                "description": "Python, Django, APIs",
                "required_skills": "Python, Django",
                "preferred_skills": "REST",
                "min_ready_score": 70,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        job_id = create_response.json()["job"]["id"]
        self.assertTrue(RecruiterJob.objects.filter(id=job_id, recruiter=self.recruiter).exists())

        dashboard_response = self.client.get(f"/api/skills/recruiter-dashboard/?job_id={job_id}")
        self.assertEqual(dashboard_response.status_code, 200)
        first_candidate = dashboard_response.json()["candidates"][0]
        self.assertIn("match_score", first_candidate)

        pipeline_response = self.client.post(
            f"/api/skills/recruiter-dashboard/pipeline/{self.student_one.id}/",
            {
                "job_id": job_id,
                "status": "shortlisted",
                "notes": "Strong backend signal",
                "tags": "python, django",
            },
            format="json",
        )
        self.assertEqual(pipeline_response.status_code, 200)
        self.assertTrue(
            RecruiterCandidatePipeline.objects.filter(
                recruiter=self.recruiter,
                candidate=self.student_one,
                job_id=job_id,
                status="shortlisted",
            ).exists()
        )

    def test_verification_steps_allow_same_step_type_for_multiple_students(self):
        VerificationStep.objects.create(
            user=self.student_one,
            step_type="profile_created",
            title="Profile Created",
            status="completed",
        )
        VerificationStep.objects.create(
            user=self.student_two,
            step_type="profile_created",
            title="Profile Created",
            status="completed",
        )

        self.assertEqual(
            VerificationStep.objects.filter(step_type="profile_created").count(),
            2,
        )

    def test_university_batch_upload_creates_students_and_scores(self):
        self.client.force_authenticate(user=self.university)
        csv_file = SimpleUploadedFile(
            "cohort.csv",
            (
                "email,full_name,college,course,branch,year_of_study,skills,placement_ready,coding_skill_index,communication_score,authenticity_score\n"
                "batchstudent@example.com,Batch Student,SkillSense University,B.Tech,CSE,2nd Year,Python;SQL,71,73,68,74\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/skills/university-dashboard/batch-upload/",
            {"file": csv_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["summary"]["created"], 1)
        imported = User.objects.get(email="batchstudent@example.com")
        self.assertEqual(imported.branch, "CSE")
        self.assertTrue(Skill.objects.filter(user=imported, name="Python").exists())
        self.assertTrue(ScoreCard.objects.filter(user=imported, score_type="placement_ready", score=71).exists())

    def test_university_intervention_updates_persist(self):
        self.client.force_authenticate(user=self.university)

        response = self.client.post(
            f"/api/skills/university-dashboard/interventions/{self.student_two.id}/",
            {
                "status": "in_progress",
                "priority": "high",
                "note": "Assign communication mentor",
                "recommended_action": "Weekly mock interviews for four weeks",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        record = InterventionRecord.objects.get(university=self.university, student=self.student_two)
        self.assertEqual(record.status, "in_progress")
        self.assertEqual(record.priority, "high")

    def test_student_evidence_resume_and_history_endpoints(self):
        CodeAnalysisReport.objects.create(
            user=self.student_one,
            repo_url="https://github.com/studentone/api-service",
            summary="API service with strong backend structure.",
            score=82,
            metrics={"files": 12},
            status="completed",
        )
        AIInterviewSession.objects.create(
            user=self.student_one,
            status="completed",
            questions=[{"question": "Tell me about Django", "difficulty": "medium"}],
            answers=[
                {
                    "question": "Tell me about Django",
                    "difficulty": "medium",
                    "answer": "I use Django to build APIs and admin workflows.",
                    "word_count": 11,
                    "points": 7,
                }
            ],
            transcript=[{"speaker": "AI", "text": "Tell me about Django"}],
            feedback=[{"type": "strength", "text": "Clear domain coverage."}],
            metrics=[{"label": "Depth", "value": 76, "color": "primary"}],
            tips=["Add deployment examples."],
            score=7,
            completed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.student_one)

        passport_response = self.client.get("/api/skills/skill-passport/")
        self.assertEqual(passport_response.status_code, 200)
        self.assertGreaterEqual(
            len(passport_response.json()["verified_skills"][0]["evidence_items"]),
            1,
        )

        resume_response = self.client.get("/api/skills/resume-builder/")
        self.assertEqual(resume_response.status_code, 200)
        self.assertEqual(resume_response.json()["full_name"], "Student One")

        interview_response = self.client.get("/api/skills/ai-interview/")
        self.assertEqual(interview_response.status_code, 200)
        self.assertGreaterEqual(len(interview_response.json()["history"]), 1)

        notifications_response = self.client.get("/api/skills/notifications/")
        self.assertEqual(notifications_response.status_code, 200)
        self.assertIn("notifications", notifications_response.json())

    def test_recruiter_can_schedule_interview_and_student_can_view_it(self):
        self.client.force_authenticate(user=self.recruiter)
        job = RecruiterJob.objects.create(
            recruiter=self.recruiter,
            title="Platform Engineer",
            description="Backend APIs and Django",
            required_skills=["Python", "Django"],
        )

        response = self.client.post(
            "/api/skills/interview-schedules/",
            {
                "candidate_id": self.student_one.id,
                "job_id": job.id,
                "title": "Platform Engineer round 1",
                "scheduled_at": timezone.now().isoformat(),
                "duration_minutes": 45,
                "meeting_link": "https://meet.example.com/platform-round-1",
                "notes": "Discuss backend architecture",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            InterviewSchedule.objects.filter(
                recruiter=self.recruiter,
                candidate=self.student_one,
                job=job,
            ).exists()
        )

        self.client.force_authenticate(user=self.student_one)
        student_view = self.client.get("/api/skills/interview-schedules/")
        self.assertEqual(student_view.status_code, 200)
        self.assertEqual(len(student_view.json()["schedules"]), 1)
        self.assertEqual(student_view.json()["schedules"][0]["recruiter_name"], "recruiter")

    def test_university_can_create_placement_drive(self):
        self.client.force_authenticate(user=self.university)

        response = self.client.post(
            "/api/skills/university-dashboard/drives/",
            {
                "company_name": "Acme Corp",
                "role_title": "Graduate Engineer",
                "description": "Campus hiring drive",
                "target_branches": "CSE,ECE",
                "target_courses": "B.Tech",
                "minimum_ready_score": 70,
                "status": "live",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["drive"]
        self.assertEqual(payload["company_name"], "Acme Corp")
        self.assertGreaterEqual(payload["eligible_count"], 1)
        self.assertTrue(
            PlacementDrive.objects.filter(university=self.university, company_name="Acme Corp").exists()
        )
