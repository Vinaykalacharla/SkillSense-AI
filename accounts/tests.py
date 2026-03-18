from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from skills.models import Document
from .models import User


class SignupResumePersistenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_student_signup_persists_resume_document(self):
        resume_file = SimpleUploadedFile(
            "resume.txt",
            b"John Example\njohn@example.com\nSkills: Python, Django",
            content_type="text/plain",
        )

        response = self.client.post(
            "/api/accounts/signup/",
            {
                "username": "johnexample",
                "full_name": "John Example",
                "email": "john@example.com",
                "password": "password123",
                "role": "student",
                "resume": resume_file,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="john@example.com")
        resume_document = Document.objects.get(user=user, doc_type="resume")
        self.assertEqual(resume_document.title, "resume.txt")
        payload = response.json()
        self.assertEqual(payload["user"]["resume_document"]["filename"], "resume.txt")
        self.assertEqual(payload["user"]["resume_document"]["download_path"], "/api/skills/resume/")

    def test_recruiter_signup_requires_approval_and_login_is_blocked(self):
        response = self.client.post(
            "/api/accounts/signup/",
            {
                "username": "campusrecruiter",
                "full_name": "Campus Recruiter",
                "organization_name": "SkillSense Hiring",
                "email": "recruiter.pending@example.com",
                "password": "password123",
                "role": "recruiter",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["requires_approval"])
        self.assertEqual(payload["user"]["approval_status"], "pending")
        self.assertNotIn("access", payload)

        login_response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "recruiter.pending@example.com",
                "password": "password123",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 403)
        self.assertEqual(login_response.json()["approval_status"], "pending")

    def test_approved_recruiter_can_login(self):
        user = User.objects.create_user(
            username="approvedrecruiter",
            email="approved.recruiter@example.com",
            password="password123",
            role="recruiter",
            organization_name="SkillSense Hiring",
            approval_status="approved",
        )

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": user.email,
                "password": "password123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["approval_status"], "approved")

    @patch.dict(
        "os.environ",
        {
            "DJANGO_SUPERUSER_EMAIL": "admin@example.com",
            "DJANGO_SUPERUSER_USERNAME": "admin",
            "DJANGO_SUPERUSER_PASSWORD": "StrongPass123!",
            "BOOTSTRAP_RECRUITER_EMAIL": "recruiter@example.com",
            "BOOTSTRAP_RECRUITER_USERNAME": "recruiter1",
            "BOOTSTRAP_RECRUITER_PASSWORD": "RecruiterPass123!",
            "BOOTSTRAP_RECRUITER_ORGANIZATION": "SkillSense Hiring",
            "BOOTSTRAP_UNIVERSITY_EMAIL": "university@example.com",
            "BOOTSTRAP_UNIVERSITY_USERNAME": "university1",
            "BOOTSTRAP_UNIVERSITY_PASSWORD": "UniversityPass123!",
            "BOOTSTRAP_UNIVERSITY_ORGANIZATION": "SkillSense University",
        },
        clear=False,
    )
    def test_bootstrap_initial_users_command_creates_accounts(self):
        call_command("bootstrap_initial_users")

        admin = User.objects.get(email="admin@example.com")
        recruiter = User.objects.get(email="recruiter@example.com")
        university = User.objects.get(email="university@example.com")

        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertEqual(recruiter.role, "recruiter")
        self.assertEqual(recruiter.approval_status, "approved")
        self.assertEqual(recruiter.organization_name, "SkillSense Hiring")
        self.assertEqual(university.role, "university")
        self.assertEqual(university.approval_status, "approved")
        self.assertEqual(university.organization_name, "SkillSense University")
