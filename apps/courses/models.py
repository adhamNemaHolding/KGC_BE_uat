import uuid

from django.db import models


class Course(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CourseId = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    Name = models.CharField(max_length=500)
    Description = models.TextField(blank=True, default="")
    Objectives = models.JSONField(default=list, blank=True)
    Category = models.CharField(max_length=255, blank=True, default="")
    SubCategory = models.CharField(max_length=255, blank=True, default="")
    Duration = models.CharField(max_length=100, blank=True, default="")
    Price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    Currency = models.CharField(max_length=10, blank=True, default="SAR")
    Link = models.URLField(max_length=1000, blank=True, default="")
    Provider = models.CharField(max_length=100, blank=True, default="KGC")
    IsActive = models.BooleanField(default=True)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Courses"

    def __str__(self) -> str:
        return self.Name


class CourseEnrollment(models.Model):
    Id = models.BigAutoField(primary_key=True)
    LmsEnrollmentId = models.BigIntegerField(null=True, blank=True)
    MerchantOrderReference = models.CharField(max_length=255)
    SponsorshipType = models.CharField(max_length=255)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "CourseEnrollments"

    def __str__(self) -> str:
        return f"Enrollment {self.Id} - {self.MerchantOrderReference}"


class CourseRating(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CustomerId = models.UUIDField(null=True, blank=True)
    CourseId = models.CharField(max_length=255, null=True, blank=True)
    Rating = models.IntegerField(null=True, blank=True)
    Review = models.TextField(null=True, blank=True)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "CourseRatings"

    def __str__(self) -> str:
        return f"Rating {self.Id} - {self.Rating}"


class KGCCandidate(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CustomerId = models.UUIDField(null=True, blank=True)
    CandidateName = models.CharField(max_length=500, null=True, blank=True)
    Email = models.CharField(max_length=255, null=True, blank=True)
    Status = models.CharField(max_length=100, null=True, blank=True)
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "KGCCandidates"

    def __str__(self) -> str:
        return self.CandidateName or f"Candidate {self.Id}"
