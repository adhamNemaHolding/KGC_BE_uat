from rest_framework import serializers

from .models import Company, CompanyMember


class CompanySerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source="Owner.Email", read_only=True)

    class Meta:
        model = Company
        fields = ["Id", "CompanyId", "Name", "Code", "owner_email", "CreatedOn", "UpdatedOn"]
        read_only_fields = ["Id", "CompanyId", "Code", "CreatedOn"]


class CompanyMemberSerializer(serializers.ModelSerializer):
    customer_email = serializers.CharField(source="Customer.Email", read_only=True)
    customer_id = serializers.UUIDField(source="Customer.CustomerId", read_only=True)
    customer_role = serializers.CharField(source="Customer.Role", read_only=True)

    class Meta:
        model = CompanyMember
        fields = ["Id", "customer_id", "customer_email", "customer_role", "JoinedOn"]
        read_only_fields = ["Id", "JoinedOn"]
