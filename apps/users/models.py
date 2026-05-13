import uuid

from django.db import models


class RoleChoices(models.TextChoices):
    USER = "user", "User"
    COMPANY = "company", "Company"


class ExperienceLevelChoices(models.TextChoices):
    ENTRY = "entry", "Entry Level"
    MID = "mid", "Mid Level"
    SENIOR = "senior", "Senior Level"
    EXECUTIVE = "executive", "Executive"


class Customer(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CustomerId = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    Email = models.CharField(max_length=255, unique=True)
    CanvasUserId = models.CharField(max_length=255, blank=True, default="")
    PasswordHash = models.CharField(max_length=500, null=True, blank=True)
    Provider = models.CharField(max_length=255, null=True, blank=True)
    IsActive = models.BooleanField(default=True)
    Role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.USER,
    )
    HasCompletedAssessment = models.BooleanField(default=False)
    AssessmentCount = models.IntegerField(default=0)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Customers"

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def __str__(self) -> str:
        return self.Email


class ProfessionalProfile(models.Model):
    Id = models.BigAutoField(primary_key=True)
    Customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="professional_profile",
        to_field="CustomerId",
    )
    AgeRange = models.CharField(max_length=20, blank=True, default="")
    IsWorking = models.BooleanField(default=False)
    CompanyName = models.CharField(max_length=255, blank=True, default="")
    CompanyIndustry = models.CharField(max_length=255, blank=True, default="")
    CurrentRole = models.CharField(max_length=255, blank=True, default="")
    TargetRole = models.CharField(max_length=255, blank=True, default="")
    ProfessionalInterests = models.JSONField(default=list, blank=True)
    CareerObjective = models.TextField(blank=True, default="")
    ExperienceLevel = models.CharField(
        max_length=20,
        choices=ExperienceLevelChoices.choices,
        blank=True,
        default="",
    )
    BiggestChallenges = models.JSONField(default=list, blank=True)
    Recommendations = models.JSONField(default=list, blank=True)
    StudyTimePerWeek = models.CharField(max_length=50, blank=True, default="")
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ProfessionalProfiles"

    def __str__(self) -> str:
        return f"{self.Customer.Email} - {self.CurrentRole}"


class CustomerEmailVerification(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CustomerId = models.UUIDField()
    IsEmailVerified = models.BooleanField(default=False)
    EmailVerificationToken = models.CharField(max_length=500, null=True, blank=True)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "CustomerEmailVerifications"

    def __str__(self) -> str:
        return f"{self.CustomerId} - verified={self.IsEmailVerified}"


class CustomerProfile(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CustomerId = models.UUIDField()
    FirstName = models.CharField(max_length=255, null=True, blank=True)
    LastName = models.CharField(max_length=255, null=True, blank=True)
    Phone = models.CharField(max_length=50, null=True, blank=True)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "CustomerProfiles"

    def __str__(self) -> str:
        return f"{self.FirstName} {self.LastName}"


class CustomerRefreshToken(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CustomerId = models.UUIDField()
    RefreshToken = models.CharField(max_length=1000, null=True, blank=True)
    ExpiresOn = models.DateTimeField(null=True, blank=True)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "CustomerRefreshTokens"

    def __str__(self) -> str:
        return f"{self.CustomerId} token"


class PasswordReset(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CustomerId = models.UUIDField()
    PasswordResetToken = models.CharField(max_length=500, null=True, blank=True)
    PasswordResetTokenExpiry = models.DateTimeField(null=True, blank=True)
    IsUsed = models.BooleanField(default=False)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "PasswordResets"

    def __str__(self) -> str:
        return f"Reset {self.Id} - used={self.IsUsed}"
