import uuid

from django.db import models


class Assessment(models.Model):
    class StatusChoices(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    Id = models.BigAutoField(primary_key=True)
    AssessmentId = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    Customer = models.ForeignKey(
        "users.Customer",
        on_delete=models.CASCADE,
        related_name="assessments",
        to_field="CustomerId",
        null=True,
        blank=True,
    )
    Title = models.CharField(max_length=255, blank=True, default="")
    Objective = models.CharField(max_length=500, blank=True, default="")
    ObjectiveBilingual = models.JSONField(default=dict, blank=True)
    Role = models.CharField(max_length=255, blank=True, default="")
    Questions = models.JSONField(default=list, blank=True)
    Responses = models.JSONField(default=list, blank=True)
    OverallProgress = models.FloatField(null=True, blank=True)
    TopStrength = models.CharField(max_length=255, blank=True, default="")
    GrowthArea = models.CharField(max_length=255, blank=True, default="")
    Skills = models.JSONField(default=list, blank=True)
    TechnicalSkills = models.JSONField(default=list, blank=True)
    Status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.IN_PROGRESS,
    )
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Assessments"

    def __str__(self) -> str:
        return f"Assessment {self.AssessmentId} - {self.Customer}"
