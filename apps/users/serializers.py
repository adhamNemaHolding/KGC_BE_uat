from rest_framework import serializers

from .models import (
    Customer,
    CustomerEmailVerification,
    CustomerProfile,
    PasswordReset,
    ProfessionalProfile,
)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "Id", "CustomerId", "Email", "CanvasUserId",
            "Provider", "IsActive", "Role",
            "HasCompletedAssessment", "AssessmentCount",
            "CreatedOn", "UpdatedOn",
        ]
        read_only_fields = ["Id", "CustomerId", "CreatedOn"]


class ProfessionalProfileSerializer(serializers.ModelSerializer):
    customer_id = serializers.UUIDField(source="Customer.CustomerId", read_only=True)

    class Meta:
        model = ProfessionalProfile
        fields = [
            "Id", "customer_id", "AgeRange", "IsWorking",
            "CompanyName", "CompanyIndustry", "CurrentRole", "TargetRole",
            "ProfessionalInterests", "CareerObjective", "ExperienceLevel",
            "BiggestChallenges", "Recommendations", "StudyTimePerWeek",
            "CreatedOn", "UpdatedOn",
        ]
        read_only_fields = ["Id", "CreatedOn"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class CustomerEmailVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerEmailVerification
        fields = "__all__"
        read_only_fields = ["Id", "CreatedOn"]


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = "__all__"
        read_only_fields = ["Id", "CreatedOn"]


class PasswordResetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordReset
        fields = ["Id", "CustomerId", "PasswordResetTokenExpiry", "IsUsed", "CreatedOn", "UpdatedOn"]
        read_only_fields = ["Id", "CreatedOn"]
