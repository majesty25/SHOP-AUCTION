from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from core import models


class CustomModelSerializer(serializers.ModelSerializer):
    @property
    def custom_full_errors(self):
        """
        Returns full errors formatted as per requirements
        """
        default_errors = self.errors  # default errors dict
        errors_messages = []
        for field_name, field_errors in default_errors.items():
            for field_error in field_errors:
                error_message = "%s: %s" % (field_name, field_error)
                errors_messages.append(
                    error_message
                )  # append error message to 'errors_messages'
        return {"errors": errors_messages}


class UserSerializer(CustomModelSerializer):
    """Serializer for the user object"""

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "name",
            "password",
            "image",
            "is_staff",
            "is_active",
            "created",
            "is_superuser",
        )
        read_only_fields = (
            "id",
            "image",
            "is_staff",
            "is_active",
            "created",
            "is_superuser",
        )
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 5,
                "style": {"input_type": "password"},
            }
        }

    def validate(self, data):
        """Check email is not updated"""
        if self.instance:
            email = data.pop("email", None)
            if email and email != self.instance.email:
                raise serializers.ValidationError("Email is immutable once set.")
        return data

    def create(self, validated_data):
        """Create and return a new user with
        encrypted password and return it"""
        user = get_user_model().objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        """Handle updating user account"""
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class AdminUserSerializer(UserSerializer):
    def create(self, validated_data):
        """Create and return a new user with
        encrypted password and return it"""
        is_staff = validated_data.pop("is_staff", None)
        is_superuser = validated_data.pop("is_superuser", None)
        is_active = validated_data.pop("is_active", None)

        if is_superuser:
            user = get_user_model().objects.create_superuser(**validated_data)
        elif is_staff:
            user = get_user_model().objects.create_staff(**validated_data)
        else:
            user = get_user_model().objects.create_user(**validated_data)

        if not is_active:
            user.is_active = False
            user.save()

        return user

    def update(self, instance, validated_data):
        """Handle updating admin user account"""
        user = super().update(instance, validated_data)

        password = validated_data.pop("password", None)
        is_staff = validated_data.pop("is_staff", None)
        is_superuser = validated_data.pop("is_superuser", None)
        is_active = validated_data.pop("is_active", None)

        if is_superuser:
            user.is_superuser = True
        else:
            user.is_superuser = False

        if is_staff:
            user.is_staff = True
        else:
            user.is_staff = False

        if is_active:
            user.is_active = True
        else:
            user.is_active = False

        user.save()

        if password:
            user.set_password(password)
            user.save()

        return user

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "name",
            "password",
            "image",
            "is_staff",
            "is_active",
            "created",
            "is_superuser",
        )
        read_only_fields = ("id", "image", "created")
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 5,
                "style": {"input_type": "password"},
            }
        }


class UserOnlySerializer(serializers.ModelSerializer):
    """Serializer for the user only object"""

    class Meta:
        model = get_user_model()
        fields = ("id", "email", "name", "image", "is_active")


class UserImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading user images"""

    class Meta:
        model = get_user_model()
        fields = ("id", "image")
        read_only_fields = ("id",)


class PasswordResetSerializer(serializers.ModelSerializer):
    """Serializer for Password reset"""

    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())

    class Meta:
        model = models.PasswordReset
        fields = (
            "reset_request",
            "validation_code",
            "verified_request",
            "reset_time",
            "user",
        )
        # read_only_fields = ('id',)


class AuthTokenSerializer(serializers.Serializer):
    """Serializer for user authentication"""

    email = serializers.CharField()
    password = serializers.CharField(
        style={"input_type": "password"},
        trim_whitespace=False,
    )

    def validate(self, attrs):
        """Validate and authenticate user"""
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )
        if not user:
            msg = _("Unable to authenticate with provided credentials")
            raise serializers.ValidationError(msg, code="authentication")

        if user.is_staff or user.is_superuser:
            msg = _("Unable to authenticate with provided credentials - Invalid base")
            raise serializers.ValidationError(msg, code="authentication")

        attrs["user"] = user
        return attrs


class AuthTokenAdminSerializer(serializers.Serializer):
    """Serializer for admin authentication"""

    email = serializers.CharField()
    password = serializers.CharField(
        style={"input_type": "password"},
        trim_whitespace=False,
    )

    def validate(self, attrs):
        """Validate and authenticate user"""
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )
        if not user:
            msg = _("Unable to authenticate with provided credentials")
            raise serializers.ValidationError(msg, code="authentication")

        if not user.is_staff:
            msg = _("Unable to authenticate with provided credentials - Invalid base 2")
            raise serializers.ValidationError(msg, code="authentication")

        attrs["user"] = user
        return attrs
