from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    name = serializers.CharField(required=False)
    organization = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'name', 'organization', 'email', 'password']

    def create(self, validated_data):
        validated_data.pop('name', None)
        validated_data.pop('organization', None)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        return user