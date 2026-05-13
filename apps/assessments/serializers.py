from rest_framework import serializers

from .models import Assessment


class AssessmentSerializer(serializers.ModelSerializer):
    customer_id = serializers.UUIDField(source="Customer.CustomerId", read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "Id", "AssessmentId", "customer_id", "Title", "Objective", "ObjectiveBilingual", "Role",
            "Questions", "Responses", "OverallProgress",
            "TopStrength", "GrowthArea", "Skills", "TechnicalSkills",
            "Status", "CreatedOn", "UpdatedOn",
        ]
        read_only_fields = ["Id", "AssessmentId", "CreatedOn"]
