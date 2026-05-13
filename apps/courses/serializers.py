from rest_framework import serializers

from .models import Course, CourseEnrollment, CourseRating, KGCCandidate


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "Id", "CourseId", "Name", "Description", "Objectives",
            "Category", "SubCategory", "Duration", "Price", "Currency",
            "Link", "Provider", "IsActive", "CreatedOn", "UpdatedOn",
        ]
        read_only_fields = ["Id", "CourseId", "CreatedOn"]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseEnrollment
        fields = "__all__"
        read_only_fields = ["Id", "CreatedOn"]


class CourseRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRating
        fields = "__all__"
        read_only_fields = ["Id", "CreatedOn"]


class KGCCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KGCCandidate
        fields = "__all__"
        read_only_fields = ["Id", "CreatedOn"]
