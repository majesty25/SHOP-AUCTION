import os
import random
import uuid
from io import BytesIO, StringIO

from django.conf import settings
# For creating user manager classes
from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
# Image Manipulation
from PIL import Image


class ResizeImageMixin:
    def resize(self, imageField: models.ImageField, size: tuple):
        im = Image.open(imageField)  # Catch original
        source_image = im.convert("RGB")
        source_image.thumbnail(size)  # Resize to size
        output = BytesIO()
        source_image.save(output, format="JPEG")  # Save resize image to bytes
        output.seek(0)

        content_file = ContentFile(
            output.read()
        )  # Read output and create ContentFile in memory
        file = File(content_file)

        random_name = f"{uuid.uuid4()}.jpeg"
        imageField.save(random_name, file, save=False)


def user_image_file_path(instance, filename):
    """Generate file path for new user profile image"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    return os.path.join("uploads/users/", filename)


class UserManager(BaseUserManager):
    """Manager for user profile"""

    def create_user(self, email, name, password=None, **extra_fields):
        """Creates and save a new user"""
        if not email:
            raise ValueError("Users must have an email address")
        if not password:
            raise ValueError("Password is required")
        if not name:
            raise ValueError("Full name is required")

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)

        user.save(using=self._db)

        random_number = random.randint(10, 99)
        ref_code = f"{random_number}{user.id}"
        user.ref_code = int(ref_code)

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password, name="HDX"):
        """Create superuser profile"""
        # User.objects.all().delete()
        user = self.create_user(email, name, password=password)

        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)

        return user

    def create_staff(self, email, name, password):
        """Create staff profile"""
        user = self.create_user(email, name, password)

        user.is_staff = True
        user.save(using=self._db)

        return user

    def create_supplier(self, email, name, password):
        """Create staff profile"""
        user = self.create_user(email, name, password)

        user.is_supplier = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin, ResizeImageMixin):
    """Database model for users in the system"""

    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255, validators=[MinLengthValidator(3)])
    is_active = models.BooleanField(default=True)
    image = models.ImageField(null=True, upload_to=user_image_file_path)

    is_supplier = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    ref_code = models.IntegerField(default=0)
    ref_source = models.IntegerField(default=0)

    objects = UserManager()

    USERNAME_FIELD = "email"
    # REQUIRED_FIELDS = ['name']

    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """On save, scale image"""
        if self.image:
            self.resize(self.image, (500, 500))

        super().save(*args, **kwargs)

    def get_full_name(self):
        """Retrieve full name of user"""
        return self.name

    def get_short_name(self):
        """Retrieve short name"""
        return self.name

    def __str__(self):
        """Return string representation of user"""
        return self.email


class PasswordReset(models.Model):
    """Reset Password Model model"""

    reset_request = models.BooleanField(default=False)
    verified_request = models.BooleanField(default=False)
    validation_code = models.CharField(max_length=255, blank=True)
    reset_time = models.DateTimeField(auto_now_add=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset",
        default=None,
    )

    def __str__(self):
        return self.user.name
