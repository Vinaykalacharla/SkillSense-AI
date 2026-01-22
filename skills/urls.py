from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='skills-dashboard'),
    path('activities/', views.activities_view, name='skills-activities'),
    path('verification-steps/', views.verification_steps_view, name='skills-verification-steps'),
    path('recommendations/', views.recommendations_view, name='skills-recommendations'),
    path('skill-suggestions/', views.skill_suggestions_view, name='skills-suggestions'),
    path('skill-passport/', views.skill_passport_view, name='skills-passport'),
    path('skill-passport/pdf/', views.skill_passport_pdf_view, name='skills-passport-pdf'),
    path('ai-interview/', views.ai_interview_view, name='skills-ai-interview'),
    path('ai-interview/action/', views.ai_interview_action_view, name='skills-ai-interview-action'),
    path('ai-generated-repos/', views.ai_generated_repos_view, name='skills-ai-generated-repos'),
    path('recruiter-dashboard/', views.recruiter_dashboard_view, name='recruiter-dashboard'),
    path('university-dashboard/', views.university_dashboard_view, name='university-dashboard'),
    path('code-analysis/', views.code_analysis_view, name='skills-code-analysis'),
    path('media/', views.media_view, name='skills-media'),
    path('progress/', views.progress_view, name='skills-progress'),
    path('roadmap/', views.roadmap_view, name='skills-roadmap'),
    path('settings/', views.settings_view, name='skills-settings'),
    path('performance/', views.performance_view, name='skills-performance'),
]
