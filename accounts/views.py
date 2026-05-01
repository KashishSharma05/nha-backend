from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import RegisterSerializer
from .models import User


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            "message": "User registered successfully",
            "username": user.username,
            "email": user.email
        }, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email
        })


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({
                "error": "Email is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)

            return Response({
                "message": "Password reset link sent successfully",
                "email": user.email
            })

        except User.DoesNotExist:
            return Response({
                "error": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)