import uuid

from django.db import models


class IndividualDevelopmentPlan(models.Model):
    Id = models.BigAutoField(primary_key=True)
    IDPId = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    Assessment = models.OneToOneField(
        "assessments.Assessment",
        on_delete=models.CASCADE,
        related_name="idp",
        to_field="AssessmentId",
    )
    Customer = models.ForeignKey(
        "users.Customer",
        on_delete=models.CASCADE,
        related_name="idps",
        to_field="CustomerId",
        null=True,
        blank=True,
    )
    TargetRole = models.CharField(max_length=255, blank=True, default="")
    CurrentLevel = models.CharField(max_length=255, blank=True, default="")
    NextMilestone = models.CharField(max_length=255, blank=True, default="")
    Timeline = models.CharField(max_length=100, blank=True, default="")
    CareerPathNote = models.TextField(blank=True, default="")
    TopStrength = models.CharField(max_length=255, blank=True, default="")
    GrowthArea = models.CharField(max_length=255, blank=True, default="")
    SkillProficiency = models.JSONField(default=list, blank=True)
    LearningRoadmap = models.JSONField(default=list, blank=True)
    GeneratedBy = models.CharField(max_length=100, blank=True, default="")
    GenerationCount = models.IntegerField(default=1)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "IndividualDevelopmentPlans"

    def __str__(self) -> str:
        return f"IDP {self.IDPId} - {self.Customer}"
