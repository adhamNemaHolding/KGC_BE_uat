from django.urls import path

from . import views

urlpatterns = [
    # AI generation
    path("generate-interests/", views.ai_generate_interests, name="ai-generate-interests"),
    path("generate-competencies/", views.ai_generate_competencies, name="ai-generate-competencies"),
    path("generate-questions/", views.ai_generate_questions, name="ai-generate-questions"),
    path("evaluate/", views.ai_evaluate_assessment, name="ai-evaluate"),
    path("generate-idp/", views.ai_generate_idp, name="ai-generate-idp"),
    # Bilingual AI generation (EN + AR simultaneously)
    path("bilingual/generate-interests/", views.ai_generate_interests_bilingual, name="ai-generate-interests-bilingual"),
    path("bilingual/generate-competencies/", views.ai_generate_competencies_bilingual, name="ai-generate-competencies-bilingual"),
    path("bilingual/generate-questions/", views.ai_generate_questions_bilingual, name="ai-generate-questions-bilingual"),
    path("bilingual/generate-idp/", views.ai_generate_idp_bilingual, name="ai-generate-idp-bilingual"),
    # IDP CRUD
    path("idps/", views.list_idps, name="list-idps"),
    path("idps/create/", views.ai_generate_idp, name="create-idp"),
    path("idps/<uuid:idp_id>/", views.get_idp, name="get-idp"),
    path("idps/<uuid:idp_id>/update/", views.update_idp, name="update-idp"),
]
