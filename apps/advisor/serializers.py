from rest_framework import serializers

from .models import IndividualDevelopmentPlan


class IDPSerializer(serializers.ModelSerializer):
    customer_id = serializers.UUIDField(source="Customer.CustomerId", read_only=True)
    assessment_id = serializers.UUIDField(source="Assessment.AssessmentId", read_only=True)

    class Meta:
        model = IndividualDevelopmentPlan
        fields = [
            "Id", "IDPId", "assessment_id", "customer_id",
            "TargetRole", "CurrentLevel", "NextMilestone", "Timeline",
            "CareerPathNote", "TopStrength", "GrowthArea",
            "SkillProficiency", "LearningRoadmap",
            "GeneratedBy", "GenerationCount", "CreatedOn", "UpdatedOn",
        ]
        read_only_fields = ["Id", "IDPId", "CreatedOn"]
