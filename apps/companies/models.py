import uuid

from django.db import models


class Company(models.Model):
    Id = models.BigAutoField(primary_key=True)
    CompanyId = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    Name = models.CharField(max_length=255, unique=True)
    Code = models.CharField(max_length=50, unique=True)
    Owner = models.ForeignKey(
        "users.Customer",
        on_delete=models.CASCADE,
        related_name="owned_companies",
        to_field="CustomerId",
    )
    CreatedOn = models.DateTimeField(auto_now_add=True)
    UpdatedOn = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Companies"

    def __str__(self) -> str:
        return self.Name


class CompanyMember(models.Model):
    Id = models.BigAutoField(primary_key=True)
    Company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="members",
        to_field="CompanyId",
    )
    Customer = models.ForeignKey(
        "users.Customer",
        on_delete=models.CASCADE,
        related_name="company_memberships",
        to_field="CustomerId",
    )
    JoinedOn = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "CompanyMembers"
        unique_together = ("Company", "Customer")

    def __str__(self) -> str:
        return f"{self.Customer} @ {self.Company}"
