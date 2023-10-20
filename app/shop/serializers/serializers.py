from django.conf import settings
from datetime import datetime, date
from django.contrib.auth import get_user_model
from django.db.models import Avg
from rest_framework import serializers

from shop.models import (Brand, Category, Media, Product, Bid, UserStats, ProductAttribute,
                         ProductAttributeValue, ProductAttributeValues,
                         ProductType)
from user.serializers import UserSerializer


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


# Categories /////////////////////
class CategorySerializer(serializers.ModelSerializer):
    """Serializer for main category object"""

    children = serializers.SerializerMethodField()
    group_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "is_active",
            "featured_name",
            "children",
            "group_count",
        )

    def get_group_count(self, obj):
        return Product.objects.filter(
            category__in=obj.get_descendants(include_self=True)
        ).count()

    def get_children(self, obj):
        return CategorySerializer(obj.get_children(), many=True).data


class CategoryNoChildrenSerializer(serializers.ModelSerializer):
    """Serializer for main category nonly object"""

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "is_active")


# Brand /////////////////////
class BrandSerializer(serializers.ModelSerializer):
    """Serializer for brand object"""

    class Meta:
        model = Brand
        fields = ("id", "name", "is_active", "is_featured")
        read_only_fields = ("id",)


class ProductTypeSerializer(serializers.ModelSerializer):
    """Serializer for ProductType object"""

    class Meta:
        model = ProductType
        fields = (
            "id",
            "name",
        )
        read_only_fields = ("id",)


# Product Attribute /////////////////////
class ProductAttributeValueSerializer(CustomModelSerializer):
    """Serializer for ProductAttributeValue"""

    name = serializers.SerializerMethodField("get_alternate_name")

    def get_alternate_name(self, obj):
        return obj.attribute_value

    class Meta:
        model = ProductAttributeValue
        # fields = ('id', 'attribute_value', 'product_attribute')
        fields = ("id", "name", "product_attribute")
        read_only_fields = ("id",)
        extra_kwargs = {
            "product_attribute": {"write_only": True},
        }


class ProductAttributeValueDetailedSerializer(ProductAttributeValueSerializer):
    """Serializer for shop product"""

    product_attribute = serializers.SerializerMethodField()

    def get_product_attribute(self, obj):
        try:
            product_att = ProductAttribute.objects.get(id=obj.product_attribute.id)
            return product_att.name
        except ProductAttribute.DoesNotExist:
            return ""

    class Meta:
        model = ProductAttributeValue
        fields = (
            "id",
            "product_attribute",
            "attribute_value",
        )


class ProductAttributeSerializer(serializers.ModelSerializer):
    """Serializer for ProductAttribute object"""

    values = ProductAttributeValueSerializer(source="product_attribute", many=True)
    category = CategoryNoChildrenSerializer(many=True)

    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "description", "category", "values")
        read_only_fields = ("id",)


class ProductAttributeNoCategorySerializer(ProductAttributeSerializer):
    """Serializer for ProductAttribute no category object"""

    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "description", "values", "is_color", "is_size")


class ProductAttributeValuesAttrSerializer(CustomModelSerializer):
    """Serializer for ProductAttributeValues"""

    class Meta:
        model = ProductAttributeValues
        fields = ("id", "attributevalues")
        read_only_fields = ("id",)


class ProductAttributeValuesSerializer(CustomModelSerializer):
    """Serializer for ProductAttributeValues"""

    class Meta:
        model = ProductAttributeValues
        fields = ("id", "attributevalues", "product")
        read_only_fields = ("id",)


# Products /////////////////////
class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading activities images"""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    uri = serializers.SerializerMethodField()
    # AWS_S3_ENDPOINT_URL

    def get_uri(self, obj):
        return f"{settings.AWS_S3_ENDPOINT_URL}{obj.image}"

    class Meta:
        model = Media
        fields = (
            "id",
            "image",
            "product",
            "is_featured",
            "default",
            "thumbnail",
            "small_image",
            "uri",
            "alt_text",
        )
        read_only_fields = ("id", "uri")


class ProductSerializer(CustomModelSerializer):
    """Serializer for shop product"""

    image = serializers.SerializerMethodField()
    # images = ProductImageSerializer(source='media_product', many=True)

    def get_image(self, product):
        try:
            qs = Media.objects.get(product=product, default=True)
            serializer = ProductImageSerializer(instance=qs)
            return serializer.data["thumbnail"]
        except Media.DoesNotExist:
            return "noimage"

    class Meta:
        model = Product
        fields = '__all__' 
        read_only_fields = ("id",)


class ProductDetailSerializer(ProductSerializer):
    """Serializer for shop product"""

    category = CategoryNoChildrenSerializer(many=True)
    product_type = ProductTypeSerializer(many=False)
    images = ProductImageSerializer(source="media_product", many=True)

    image = serializers.SerializerMethodField()
    uri = serializers.SerializerMethodField()

    attribute_values = ProductAttributeValueDetailedSerializer(many=True)
    user = UserSerializer()

    def get_image(self, product):
        try:
            qs = Media.objects.get(product=product, default=True)
            serializer = ProductImageSerializer(instance=qs)
            return serializer.data["thumbnail"]
        except Media.DoesNotExist:
            return "noimage"

    def get_uri(self, product):
        try:
            qs = Media.objects.get(product=product, default=True)
            serializer = ProductImageSerializer(instance=qs)
            return serializer.data["thumbnail"]
        except Media.DoesNotExist:
            return "noimage"

    class Meta:
        model = Product
        fields = '__all__'
        extra_fields = ['images', 'uri']
        read_only_fields = ("id",)


class BidSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ('id', 'auction', 'is_active', 'bid_amount', 'bid_time', 'bid_amount')
        read_only_fields = ("id",)

class UserStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStats
        fields = ('id', 'auction', 'view_timestamp', 'bid_count')


class CustomDateField(serializers.ReadOnlyField):
    def to_representation(self, value):
        if value:
            # Format the date as the full weekday name (e.g., Monday)
            return value.strftime('%A')
            
        return None

class BidChartSerializer(serializers.Serializer):
    bid_time__date = CustomDateField()  # Use the custom date field
    bid_count = serializers.IntegerField()

    def __init__(self, bid_data, *args, **kwargs):
        super(BidChartSerializer, self).__init__(*args, **kwargs)
        self.bid_data__date = bid_data

    def to_representation(self, instance):
        # Map bid_time__date to bid_count
        return {
            'bid_date': instance['bid_time__date'],
            'bid_count': instance['bid_count']
        }
    
    
class ViewChartSerializer(serializers.Serializer):
    view_timestamp__date = CustomDateField()  # Define the custom date field for the view time
    view_count = serializers.IntegerField()


    def __init__(self, view_data, *args, **kwargs):
        super(ViewChartSerializer, self).__init__(*args, **kwargs)
        self.view_data = view_data

    def to_representation(self, instance):
        # Map view_date to view_count
        return {
            'view_date': instance['view_date'],
            'view_count': instance['view_count']
        }

# class WishlistSerializer(serializers.ModelSerializer):
#     """Serializer for wishlist"""

#     class Meta:
#         model = Wishlist
#         fields = ('id', 'product', 'user')
#         read_only = ('id')

# class WishlistDetailsSerializer(serializers.ModelSerializer):
#     """Serializer for wishlist detail"""
#     product = ProductSerializer(many=False)

#     class Meta:
#         model = Wishlist
#         fields = ('id', 'product', 'user')
#         read_only = ('id')
