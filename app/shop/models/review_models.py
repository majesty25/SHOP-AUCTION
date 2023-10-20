# from django.db import models
# from django.utils.translation import gettext_lazy as _
# from django.conf import settings
# from django.core.validators import MaxValueValidator, MinValueValidator

# from .base_models import Product, ResizeImageMixin, review_image_file_path, review_image_file_path_thumb

# class Review(models.Model):
#     rating = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
#     review = models.CharField(max_length=1000, blank=True, default='')
#     created_at = models.DateTimeField(
#         auto_now_add=True,
#         editable=False,
#     )
#     approved = models.BooleanField(default=False,)
#     updated_at = models.DateTimeField(
#         auto_now=True,
#     )
#     product = models.ForeignKey(
#         Product,
#         related_name="review_product",
#         on_delete=models.CASCADE,
#     )
#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete = models.CASCADE,
#         related_name="review_user"
#     )


#     class Meta:
#         ordering = ('created_at',)
#         unique_together = (("product", "user"),)

#     def __str__(self):
#         return f"{self.product.name} - {self.review}"


# class ReviewImage(models.Model, ResizeImageMixin):
#     review = models.ForeignKey(
#         "Review",
#         on_delete=models.CASCADE,
#     )
#     image = models.ImageField(upload_to=review_image_file_path)
#     thumbnail = models.ImageField(
#         unique=False,
#         null=False,
#         blank=True,
#         upload_to=review_image_file_path_thumb,
#         default="images/default.png",
#     )

#     def save(self, *args, **kwargs):
#         ''' On save, scale thumbnail '''
#         if self.image.height > 1500 or self.image.width > 1500:
#             self.resize(self.image, (1500, 1500))
#         if self.image:
#             self.resize(self.thumbnail, (400, 400))

#         super().save(*args, **kwargs)
