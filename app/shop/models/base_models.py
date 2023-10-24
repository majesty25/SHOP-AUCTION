from datetime import datetime
import os
import uuid
from io import BytesIO, StringIO
from itertools import product
from django.utils import timezone
from firebase_admin import storage
from django.contrib.postgres.fields import ArrayField

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField
from PIL import Image


AMOUNT_BIDDING = 'amount_bidding'
PERCANTAGE = 'percentage'
CUSTOM_AMOUNT = 'custom_amount'
BUYER_DEPOSITS = [
    (AMOUNT_BIDDING, _('amount_bidding')),
    (PERCANTAGE, _('percentage')),
    (CUSTOM_AMOUNT, _('custom_amount')),
]
BUYER_DEPOSITS_LIST = [
    AMOUNT_BIDDING,
    PERCANTAGE,
    CUSTOM_AMOUNT,
]

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


def product_image_file_path(instance, filename):
    """Generate file path for new product image"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    return os.path.join(f"uploads/shop/products/{instance.product.id}/", filename)


def product_image_file_path_thumb(instance, filename):
    """Generate file path for new product thumb image"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    return os.path.join(f"uploads/shop/products/{instance.product.id}/thumb/", filename)


def product_image_file_path_small(instance, filename):
    """Generate file path for new product thumb image"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    return os.path.join(f"uploads/shop/products/{instance.product.id}/small/", filename)


def review_image_file_path(instance, filename):
    """Generate file path for new review image"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    return os.path.join(f"uploads/shop/reviews/{instance.review.id}/", filename)


def review_image_file_path_thumb(instance, filename):
    """Generate file path for new review thumb image"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    return os.path.join(f"uploads/shop/reviews/{instance.review.id}/thumb/", filename)


class Category(MPTTModel):
    """
    Products Category table implimented with MPTT
    """

    name = models.CharField(
        max_length=100,
        null=False,
        unique=False,
        blank=False,
        verbose_name=_("category name"),
        help_text=_("format: required, max-100"),
    )
    slug = models.SlugField(
        max_length=150,
        null=False,
        unique=False,
        blank=False,
        verbose_name=_("category safe URL"),
        help_text=_("format: required, letters, numbers, underscore, or hyphens"),
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_featured = models.BooleanField(
        default=False,
    )
    is_nav = models.BooleanField(
        default=False,
    )
    nav_order = models.IntegerField(default=0)
    featured_name = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        unique=False,
        default="",
    )
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        unique=False,
        verbose_name=_("parent of category"),
        help_text=_("format: not required"),
    )

    def get_full_name(self):
        names = self.get_ancestors(include_self=True).values("name")
        full_name = " - ".join(map(lambda x: x["name"], names))
        return full_name

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = _("product category")
        verbose_name_plural = _("product categories")

    def __str__(self):
        return self.name


class ProductType(models.Model):
    """
    Product type table
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        verbose_name=_("type of product"),
        help_text=_("format: required, unique, max-255"),
    )

    def __str__(self):
        return self.name


class Brand(models.Model):
    """
    Product brand table
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        verbose_name=_("brand name"),
        help_text=_("format: required, unique, max-255"),
    )
    is_featured = models.BooleanField(
        default=False,
    )
    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


class ProductAttribute(models.Model):
    """
    Product attribute table
    """

    category = TreeManyToManyField(Category)
    name = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        verbose_name=_("product attribute name"),
        help_text=_("format: required, unique, max-255"),
    )
    slug = models.SlugField(
        max_length=150,
        null=False,
        unique=True,
        blank=False,
        verbose_name=_("product attribute safe URL"),
        help_text=_("format: required, letters, numbers, underscore, or hyphens"),
    )
    is_color = models.BooleanField(
        default=False,
    )
    is_size = models.BooleanField(
        default=False,
    )
    description = models.TextField(
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("product attribute description"),
        help_text=_("format: required"),
    )

    def __str__(self):
        return self.name


class ProductAttributeValue(models.Model):
    """
    Product attribute value table
    """

    product_attribute = models.ForeignKey(
        ProductAttribute,
        related_name="product_attribute",
        on_delete=models.PROTECT,
    )
    attribute_value = models.CharField(
        max_length=255,
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("attribute value"),
        help_text=_("format: required, max-255"),
    )

    def __str__(self):
        return f"{self.product_attribute.name} : {self.attribute_value}"


class Product(models.Model):
    """
    Product details table
    """

    slug = models.SlugField(
        max_length=255,
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("product safe URL"),
        help_text=_("format: required, letters, numbers, underscores or hyphens"),
    )
    name = models.CharField(
        max_length=255,
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("product name"),
        help_text=_("format: required, max-255"),
    )
    description = models.TextField(
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("product description"),
        help_text=_("format: required"),
    )
    category = TreeManyToManyField(Category)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_user"
    )
    is_active = models.BooleanField(
        default=True,
    )
    status = models.BooleanField(
        unique=False,
        null=False,
        blank=False,
        default=True,
        # verbose_name=_("product status"),
        # help_text=_("format: true=product visible (Online or Offline)"),
    )
    is_featured = models.BooleanField(
        unique=False,
        null=False,
        blank=False,
        default=True,
    )
    edited = models.BooleanField(unique=False, null=False, blank=False, default=False)
    priority = models.IntegerField(default=0)
    product_type = models.ForeignKey(
        ProductType,
        related_name="product_type",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    brand = models.ForeignKey(
        Brand,
        related_name="brand",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    attribute_values = models.ManyToManyField(
        ProductAttributeValue,
        related_name="product_attribute_values",
        through="ProductAttributeValues",
    )
    starting_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        unique=False,
        null=True,
        blank=True,
        help_text=_("format: maximum price 999999.99"),
        error_messages={
            "name": {
                "max_length": _("the price must be between 0 and 999999.99."),
            },
        },
    )
    reserve_price_status = models.BooleanField(
        default=False,
    )
    reserve_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        unique=False,
        default=0.00,
        help_text=_("format: maximum price 999999.99"),
        error_messages={
            "name": {
                "max_length": _("the price must be between 0 and 999999.99."),
            },
        },
    )
    buy_now_status = models.BooleanField(
        default=False,
    )
    buy_now_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        unique=False,
        default=0.00,
        help_text=_("format: maximum price 999999.99"),
        error_messages={
            "name": {
                "max_length": _("the price must be between 0 and 999999.99."),
            },
        },
    )
    buyer_deposit_status = models.BooleanField(
        default=False,
    )
    buyer_deposit_type = models.CharField(
        max_length=225,
        choices=BUYER_DEPOSITS,
        default=AMOUNT_BIDDING,
    )
    buyer_deposit = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        unique=False,
        default=0.00,
        help_text=_("format: maximum price 999999.99"),
        error_messages={
            "name": {
                "max_length": _("the price must be between 0 and 999999.99."),
            },
        },
    )
    region = models.CharField(
        max_length=255,
        unique=False,
        null=False,
        blank=False,
    )
    city = models.CharField(
        max_length=255,
        unique=False,
        null=False,
        blank=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name=_("date product created"),
        help_text=_("format: Y-m-d H:M:S"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("date product last updated"),
        help_text=_("format: Y-m-d H:M:S"),
    )
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    current_highest_bid= models.DecimalField(max_digits=10, decimal_places=2, null=True)
    bidding_step = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = (("user", "slug"),)
        ordering = ["-priority", "-created_at"]


class Media(models.Model, ResizeImageMixin):
    """
    The product image table.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="media_product",
    )
    image = models.ImageField(
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("product image"),
        upload_to=product_image_file_path,
        default="images/default.png",
        help_text=_("format: required, default-default.png"),
    )
    thumbnail = models.ImageField(
        unique=False,
        null=False,
        blank=True,
        verbose_name=_("product image thumbnail"),
        upload_to=product_image_file_path_thumb,
        default="images/default.png",
        help_text=_("format: required, default-default.png"),
    )
    small_image = models.ImageField(
        unique=False,
        null=False,
        blank=True,
        verbose_name=_("product image small"),
        upload_to=product_image_file_path_small,
        default="images/default.png",
        help_text=_("format: required, default-default.png"),
    )
    alt_text = models.CharField(
        max_length=255,
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("alternative text"),
        help_text=_("format: required, max-255"),
    )
    is_featured = models.BooleanField(
        default=True,
        verbose_name=_("show product image"),
        help_text=_("format: default=false, true=default image"),
    )
    default = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name=_("product visibility"),
        help_text=_("format: Y-m-d H:M:S"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("date sub-product created"),
        help_text=_("format: Y-m-d H:M:S"),
    )

    class Meta:
        verbose_name = _("product image")
        verbose_name_plural = _("product images")

    def save(self, *args, **kwargs):
        """On save, scale thumbnail"""
        if self.image.height > 1500 or self.image.width > 1500:
            self.resize(self.image, (1500, 1500))
        if self.image:
            self.resize(self.thumbnail, (800, 800))
            self.resize(self.small_image, (400, 400))

        super().save(*args, **kwargs)


class ProductAttributeValues(models.Model):
    """
    Product attribute values link table
    """

    attributevalues = models.ForeignKey(
        "ProductAttributeValue",
        related_name="attributevaluess",
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        Product,
        related_name="productattributevaluess",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.product.name} - {self.attributevalues.attribute_value}"

    class Meta:
        unique_together = (("attributevalues", "product"),)


class Bid(models.Model):
    auction = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete = models.CASCADE,
            related_name="bidder"
        )
    is_active = models.BooleanField(default=True)
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bid_time = models.DateTimeField(default=timezone.now)
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)    

    def __str__(self):
        return f'Bid of ${self.bid_amount} on {self.auction.name} by {self.bidder.name}'


class UserStats(models.Model):
    user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete = models.CASCADE,
            related_name="stat"
        )
    auction = models.ForeignKey(Product, on_delete=models.CASCADE)
    view_timestamp = models.DateTimeField(default=timezone.now)
    bid_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user} - {self.auction} - {self.view_timestamp}"


class ProductMedia(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    main_picture = models.CharField(max_length=255, blank=True, null=True)
    thumbnail = models.CharField(max_length=255, blank=True, null=True)

class ProductImages(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    image = models.CharField(max_length=255, null=True, blank=True)