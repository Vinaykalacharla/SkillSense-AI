from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Skill(models.Model):
    SKILL_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='beginner')
    score = models.IntegerField(default=0, help_text='Skill score out of 100')
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'name']
        verbose_name = _('Skill')
        verbose_name_plural = _('Skills')

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.level})"

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('code_upload', 'Code Upload'),
        ('document_upload', 'Document Upload'),
        ('video_interview', 'Video Interview'),
        ('skill_verification', 'Skill Verification'),
        ('badge_earned', 'Badge Earned'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ScoreCard(models.Model):
    SCORE_TYPES = [
        ('coding_skill_index', 'Coding Skill Index'),
        ('communication_score', 'Communication Score'),
        ('authenticity_score', 'Authenticity Score'),
        ('placement_ready', 'Placement Ready'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scorecards')
    score_type = models.CharField(max_length=30, choices=SCORE_TYPES)
    score = models.IntegerField(default=0, help_text='Score out of 100')
    change = models.IntegerField(default=0, help_text='Change from previous score')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'score_type']
        verbose_name = _('Score Card')
        verbose_name_plural = _('Score Cards')

    def __str__(self):
        return f"{self.user.username} - {self.score_type}: {self.score}"


class ScoreSnapshot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='score_snapshots')
    recorded_on = models.DateField()
    scores = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'recorded_on']
        verbose_name = _('Score Snapshot')
        verbose_name_plural = _('Score Snapshots')
        ordering = ['recorded_on']

    def __str__(self):
        return f"{self.user.username} - {self.recorded_on}"

class VerificationStep(models.Model):
    STEP_TYPES = [
        ('profile_created', 'Profile Created'),
        ('first_code_upload', 'First Code Upload'),
        ('skills_extracted', 'Skills Extracted'),
        ('ai_interview_completed', 'AI Interview Completed'),
        ('skill_verification', 'Skill Verification'),
        ('document_verification', 'Document Verification'),
        ('skill_passport_ready', 'Skill Passport Ready'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('current', 'Current'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_steps')
    step_type = models.CharField(max_length=30, choices=STEP_TYPES, unique=True)
    title = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'step_type']
        verbose_name = _('Verification Step')
        verbose_name_plural = _('Verification Steps')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class Document(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('reviewing', 'Reviewing'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to='documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class AIInterviewSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_interviews')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    transcript = models.JSONField(default=list)
    feedback = models.JSONField(default=list)
    metrics = models.JSONField(default=list)
    tips = models.JSONField(default=list)
    questions = models.JSONField(default=list)
    answers = models.JSONField(default=list)
    current_index = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = _('AI Interview Session')
        verbose_name_plural = _('AI Interview Sessions')

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class ProjectSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewing', 'Reviewing'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    title = models.CharField(max_length=200)
    repo_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Project Submission')
        verbose_name_plural = _('Project Submissions')

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class CodeAnalysisReport(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_analysis_reports')
    repo_url = models.URLField()
    summary = models.TextField(blank=True)
    score = models.IntegerField(default=0)
    metrics = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Code Analysis Report')
        verbose_name_plural = _('Code Analysis Reports')

    def __str__(self):
        return f"{self.user.username} - {self.repo_url}"


class MediaUpload(models.Model):
    MEDIA_TYPES = [
        ('video', 'Video'),
        ('audio', 'Audio'),
    ]

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_uploads')
    title = models.CharField(max_length=200)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    file = models.FileField(upload_to='media/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Media Upload')
        verbose_name_plural = _('Media Uploads')

    def __str__(self):
        return f"{self.user.username} - {self.title}"
