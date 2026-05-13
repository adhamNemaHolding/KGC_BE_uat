from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_assessments, name="list-assessments"),
    path("create/", views.create_assessment, name="create-assessment"),
    path("<uuid:assessment_id>/", views.get_assessment, name="get-assessment"),
    path("<uuid:assessment_id>/update/", views.update_assessment, name="update-assessment"),
]
