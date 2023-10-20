import os
import random
import re
from datetime import datetime, timedelta
from distutils import errors
from email import message

from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import (authentication, generics, mixins, permissions,
                            serializers, status, viewsets)
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
# For authentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import (action, api_view,
                                       authentication_classes,
                                       permission_classes)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings

from core import permissions
from core.models import PasswordReset
from core.utils import (StandardAdminResultsSetPagination, create_error_data,
                        create_message_data, email_compose, mock_if_true,
                        send_mail, send_mail_mailgun)
from user.serializers import (AdminUserSerializer, AuthTokenAdminSerializer,
                              AuthTokenSerializer, PasswordResetSerializer,
                              UserImageSerializer, UserSerializer)


@api_view(["GET"])
def hello_world(request):
    return Response(data={"message": "Hello World"}, status=status.HTTP_200_OK)


class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system"""

    serializer_class = UserSerializer

    def raise_error(self, msg):
        msg = [msg]
        error_data = {"errors": msg}
        raise serializers.ValidationError(error_data, code="registration")

    def get_serializer_class(self):
        """Return appropriate serializer class"""

        return self.serializer_class

    def perform_create(self, serializer):
        """Create a new user"""

        validated_data = self.request.data

        password = validated_data.get("password", None)
        confirm_password = validated_data.get("confirm_password", None)
        email = validated_data.get("email", None)
        is_superuser = validated_data.get("name", None)
        is_staff = validated_data.get("name", None)
        name = validated_data.get("name", None)
        name = validated_data.get("name", None)

        if password != confirm_password:
            self.raise_error("Passwords does not match")
        if len(password) < 6:
            self.raise_error(f"Password should be 6 or more characters")

        serializer.save(name=name, email=email, password=password)


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user"""

    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def post(self, request, *args, **kwargs):
        validated_data = self.request.data
        if validated_data.get("is_admin"):
            serializer = AuthTokenAdminSerializer(
                data=request.data, context={"request": request}
            )
        else:
            serializer = self.serializer_class(
                data=request.data, context={"request": request}
            )

        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)

        user_data = UserSerializer(user)
        user_id = f"{user.id}"
        return Response({"token": token.key, "user": user_data.data})


class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user"""

    serializer_class = UserSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        return self.serializer_class

    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user


class UserImageViewset(
    generics.RetrieveUpdateAPIView,
):
    """Manage Images in database"""

    serializer_class = UserImageSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


# Reset password
@api_view(["POST"])
def password_reset(request):
    """
    Send Email to user
    """

    response_format = {}
    data = request.data
    try:
        snippet = get_user_model().objects.get(email=data["email"])
    except get_user_model().DoesNotExist:
        errors = create_error_data("User with email does not exist")
        return Response(data=errors, status=status.HTTP_404_NOT_FOUND)

    userData = snippet
    random_number = random.randint(100000, 999999)
    userData.code = random_number
    password_reset_data = {
        "reset_request": True,
        "validation_code": random_number,
        "reset_time": timezone.now(),
        "user": userData.id,
    }

    try:
        user_password_reset = PasswordReset.objects.get(user=userData.id)
        if user_password_reset:
            serializer = PasswordResetSerializer(
                user_password_reset, data=password_reset_data
            )
    except PasswordReset.DoesNotExist:
        serializer = PasswordResetSerializer(data=password_reset_data)

    if serializer.is_valid():
        serializer.save()
        mock = mock_if_true()
        if not mock:
            mail = email_compose(type="reset-password", data=userData)
            # send_simple_message()
            send_mail_mailgun(
                email=data["email"], value=mail["emailContent"], subject=mail["subject"]
            )
            # send_mail(
            #     email=data["email"], value=mail["emailContent"], subject=mail["subject"]
            # )
            message = create_message_data(
                "Reset code sent susscessfully to email provided"
            )
            return Response(data=message, status=status.HTTP_200_OK)
        else:
            message = create_message_data(
                "Reset code sent susscessfully to email provided (mocked)"
            )
            return Response(data=message, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Reset password
@api_view(["POST"])
def password_reset_verify(request):
    """
    Verify password verification code
    """

    data = request.data
    try:
        snippet = get_user_model().objects.get(email=data["email"])
    except get_user_model().DoesNotExist:
        errors = create_error_data("User with email does not exist")
        return Response(data=errors, status=status.HTTP_404_NOT_FOUND)

    userData = snippet

    try:
        snippet = PasswordReset.objects.get(user=userData.id)
    except PasswordReset.DoesNotExist:
        errors = create_error_data("Verification failed")
        return Response(data=errors, status=status.HTTP_404_NOT_FOUND)

    try:
        snippet = PasswordReset.objects.get(
            user=userData.id, validation_code=data["code"], reset_request=True
        )
    except PasswordReset.DoesNotExist:
        errors = create_error_data("Invalid verification code")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

    allowed_time = timezone.now() - timedelta(minutes=30)
    reset_snippet = PasswordReset.objects.filter(
        user=userData.id,
        validation_code=data["code"],
        reset_request=True,
        reset_time__gte=allowed_time,
    )
    if not reset_snippet:
        errors = create_error_data("Time elapsed for verification")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        password_reset_data = {
            "reset_request": False,
            "verified_request": True,
            "validation_code": 0,
            "reset_time": timezone.now(),
            "user": userData.id,
        }

        serializer = PasswordResetSerializer(snippet, data=password_reset_data)
        if serializer.is_valid():
            serializer.save()
            message = create_message_data("Code successfully verified")
            return Response(data=message, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Reset password
@api_view(["POST"])
def password_reset_change(request):
    """
    change password after verification
    """

    data = request.data

    confirmPassword = request.data.get("confirmPassword") or 0
    password = request.data.get("password") or 0

    if not password:
        errors = create_error_data("Password is required")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

    if password and confirmPassword != password:
        return Response(
            data="Passwords do not match", status=status.HTTP_400_BAD_REQUEST
        )

    try:
        snippet = get_user_model().objects.get(email=data["email"])
    except get_user_model().DoesNotExist:
        errors = create_error_data("User with email does not exist")
        return Response(data=errors, status=status.HTTP_404_NOT_FOUND)

    userData = snippet

    try:
        snippet = PasswordReset.objects.get(user=userData.id)
    except PasswordReset.DoesNotExist:
        errors = create_error_data("Verification failed")
        return Response(data=errors, status=status.HTTP_404_NOT_FOUND)

    try:
        snippet = PasswordReset.objects.get(user=userData.id, verified_request=True)
    except PasswordReset.DoesNotExist:
        errors = create_error_data("Invalid verification data")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

    allowed_time = timezone.now() - timedelta(minutes=30)
    reset_snippet = PasswordReset.objects.filter(
        user=userData.id, verified_request=True, reset_time__gte=allowed_time
    )
    if not reset_snippet:
        errors = create_error_data("Time elapsed for reset password")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        user = get_user_model().objects.get(id=userData.id)
        user.set_password(password)
        user.save()

        password_reset_data = {
            "reset_request": False,
            "verified_request": False,
            "validation_code": 0,
            "reset_time": timezone.now(),
            "user": userData.id,
        }

        serializer = PasswordResetSerializer(snippet, data=password_reset_data)
        if serializer.is_valid():
            serializer.save()
            message = create_message_data("Password successfully changed")
            return Response(data=message, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Admin Backend Views & Viewsets
class AdminNonProUsersViewSet(
    viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin
):
    """Retrive and list non pro users for admin"""

    serializer_class = UserSerializer
    queryset = (
        get_user_model()
        .objects.filter(is_staff=False, is_superuser=False)
        .order_by("-id")
    )
    pagination_class = StandardAdminResultsSetPagination
    permission_classes = (permissions.allowOnlyAuthenticatedAdmins,)
    authentication_classes = (TokenAuthentication,)

    def get_queryset(self):
        """Return objects for the current authenticated user only"""
        queryset = self.queryset

        # Get query params
        keywords = self.request.query_params.get("keywords") or ""

        if keywords:
            queryset = queryset.annotate(
                search=SearchVector("name"),
            ).filter(search=keywords)

        return queryset.distinct()


@api_view(["POST"])
@authentication_classes((TokenAuthentication,))
@permission_classes((permissions.allowOnlyAuthenticatedAdmins,))
def activate_deactivate_user(request):
    """activate user"""
    user_id = request.data.get("userId") or None
    action = request.data.get("action") or None

    try:
        user = get_user_model().objects.get(
            id=user_id, is_staff=False, is_superuser=False
        )
        try:
            if user and user.is_active == False and action == "activate":
                user.is_active = True
                user.save()
                return Response(
                    data="User activated successfully", status=status.HTTP_200_OK
                )
            elif user and user.is_active == True and action == "deactivate":
                user.is_active = False
                user.save()
                return Response(
                    data="user Deactivated successfully", status=status.HTTP_200_OK
                )
            else:
                return Response(
                    data=f"Invalid action {action} for user status {user.is_active}",
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
    except get_user_model().DoesNotExist:
        return Response(data="User Does not exist", status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def validate_user_email(request):
    """validate user email"""
    user_email = request.data.get("email") or None
    if not user_email:
        errors = create_error_data("Email is required")
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        if get_user_model().objects.filter(email=user_email).exists():
            message = create_message_data(f"User with email {user_email} exists")
            return Response(data=message, status=status.HTTP_200_OK)
        else:
            errors = create_error_data(f"User with {user_email} Does not exists")
            return Response(data=errors, status=status.HTTP_404_NOT_FOUND)
    except get_user_model().DoesNotExist:
        errors = create_error_data("Ooops an error occured")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def validate_user_phone(request):
    """validate user phone"""
    user_phone = request.data.get("phone") or None
    if not user_phone:
        errors = create_error_data("Phone is required")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        if get_user_model().objects.filter(phone=user_phone).exists():
            message = create_message_data(
                f"User already exists with phone {user_phone}"
            )
            return Response(data=message, status=status.HTTP_200_OK)
        else:
            errors = create_error_data(f"User with {user_phone} Does not exist")
            return Response(data=errors, status=status.HTTP_200_OK)
    except get_user_model().DoesNotExist:
        errors = create_error_data("Ooops an error occured")
        return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)


class ManageAdminUserViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
):
    """Create a new admin user in the system"""

    serializer_class = AdminUserSerializer
    queryset = (
        get_user_model()
        .objects.filter(Q(is_superuser=True) | Q(is_staff=True))
        .order_by("-id")
    )
    permission_classes = (permissions.allowOnlyAuthenticatedSuperAdmins,)
    authentication_classes = (TokenAuthentication,)
