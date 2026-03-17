from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

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
