from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext as _

from shop import models

admin.site.register(models.Category)
admin.site.register(models.Media)
admin.site.register(models.Product)
admin.site.register(models.Bid)
admin.site.register(models.UserStats)
admin.site.register(models.ProductAttribute)
admin.site.register(models.ProductAttributeValue)
admin.site.register(models.ProductAttributeValues)
admin.site.register(models.ProductType)
admin.site.register(models.Brand)
