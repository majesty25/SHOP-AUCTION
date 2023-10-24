from datetime import datetime, timedelta
from django.utils import timezone
import json
from html import unescape
import firebase_admin
import requests
import os
import uuid
from firebase_admin import storage
from firebase_admin.credentials import Certificate
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

from itertools import product
from django.db.models import Sum
from django.http import HttpResponse

from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.contrib.postgres.search import SearchVector
from django.db.models import Count, Q
from core.permissions import (IsAuctionOwner)
from rest_framework import (authentication, mixins, generics, serializers, status,
                            viewsets, filters)
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import NotFound


from core import permissions
from core.utils import (StandardResultsSetPagination, clean_url,
                        create_error_data, create_message_data)
from shop.models import (Category, Media, Product,ProductImages, ProductMedia, Bid, ProductAttribute, UserStats,
                         ProductAttributeValues)
from shop.serializers import (CategorySerializer,
                              ProductAttributeNoCategorySerializer,
                              ProductAttributeSerializer,
                              BidSerializer,                              
                              UserStatsSerializer,
                              FileUploadSerializer,
                              BidChartSerializer,
                              ImageSerializer,
                              ViewChartSerializer,
                              ProductMediaSerializer,
                              ProductAttributeValuesAttrSerializer,
                              ProductAttributeValuesSerializer,
                              ProductDetailSerializer, ProductImageSerializer,
                              ProductSerializer)


class ShopCategoryViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    """Manages shop categories in database"""

    serializer_class = CategorySerializer
    queryset = Category.objects.filter(level=0, is_active=True)


class ProductAttributesViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
):
    """Manages product attributes in database"""

    serializer_class = ProductAttributeSerializer
    queryset = ProductAttribute.objects.all()

    @action(
        methods=["GET"],
        detail=False,
        url_path="category-attributes/(?P<category_id>\d+)",
    )
    def category_attributes(self, request, category_id):
        """Get attributes related to category"""
        try:
            category = Category.objects.get(id=category_id)
            product_attributes = ProductAttribute.objects.filter(
                category__in=category.get_family()
            ).distinct()
            # product_attributes = ProductAttribute.objects.filter(category__in=category) get_descendants
            product_attr_serializer = ProductAttributeNoCategorySerializer(
                product_attributes, many=True
            )
            return Response(product_attr_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


class PublicProductViewSet(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
):
    """Retrive and list activities"""

    serializer_class = ProductSerializer
    queryset = Product.objects.filter(
        is_active=True, status=True, user__is_active=True
    ).order_by("-priority")
    pagination_class = StandardResultsSetPagination
    authentication_classes = (TokenAuthentication,)
    permission_classes = (
        AllowAny,
        permissions.UpdateOwnObject,
    )

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == "retrieve":
            return ProductDetailSerializer
        return self.serializer_class

    def _params_to_ints(self, qs):
        """Convert a list of string IDS to list of Integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def raise_error(self, msg):
        msg = [msg]
        error_data = {"errors": msg}
        raise serializers.ValidationError(error_data, code="authentication")

    def get_queryset(self):
        """Return objects for the current authenticated user only"""
        queryset = self.queryset

        if (
            (
                self.action == "retrieve"
                or self.action == "update"
                or self.action == "destroy"
            )
            and self.request.user.is_authenticated
        ):
            queryset = Product.objects.filter(
                Q(user__is_active=True, is_active=True)
                | Q(user__id=self.request.user.id, is_active=False)
            ).order_by("-name")

        if self.action == "product_search":
            filterData = self.request.data
        else:
            filterData = self.request.query_params

        # Get query params
        category = filterData.get("category") or 0
        region = filterData.get("region") or 0
        city = filterData.get("city") or 0
        country = filterData.get("country") or 0
        featured = filterData.get("featured") or 0
        most_appreciated = filterData.get("appreciated") or 0
        recent = filterData.get("recent") or 0
        keywords = filterData.get("keywords") or ""
        user_id = filterData.get("user_id") or 0

        if city and city != "":
            queryset = queryset.filter(city__iexact=city)
        if region and region != "":
            queryset = queryset.filter(region__iexact=region)
        if int(user_id) > 0:
            queryset = queryset.filter(user__id=user_id)
        if int(category) > 0:
            category = Category.objects.get(id=category)
            queryset = queryset.filter(
                category__in=category.get_descendants(include_self=True)
            )
        if int(featured) == 1:
            queryset = queryset.filter(featured=True)
        if int(recent) == 1:
            queryset = queryset.order_by("-id")
        if int(most_appreciated) == 1:
            queryset = queryset.annotate(q_count=Count("likes")).order_by("-q_count")
        if keywords:
            queryset = queryset.annotate(
                search=SearchVector("name", "description"),
            ).filter(search=keywords)

        if country:
            queryset = queryset.filter(user__professionaluser__country=country)

        return queryset.distinct()

    def validate_request_data(self, request):
        request_data = request.data.copy()
        name = request_data.get("name") or None
        attributes_json = request_data.get("attributes")
        attributes = attributes_json and json.loads(attributes_json) or None
        images = request_data.get("images[0]") or None

        if name:
            url_title = clean_url(name)
            request_data.update({"slug": url_title})

        if not images and self.action != "update":
            self.raise_error("At least one image is required")
        if attributes and not isinstance(attributes, list):
            self.raise_error("Attributes data must be a list")

        if attributes:
            for attribute in attributes:
                attr_serializer = ProductAttributeValuesAttrSerializer(
                    data={"attributevalues": attribute}
                )
                if not attr_serializer.is_valid():
                    raise serializers.ValidationError(attr_serializer.errors)

        return request_data

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        request_data = self.validate_request_data(request)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Update product"""

        validated_data = self.request.data
        self.save_data(serializer=serializer, validated_data=validated_data)

    def create(self, request, *args, **kwargs):
        request_data = self.validate_request_data(request)
        request_data["user"] = self.request.user.id
        serializer = self.get_serializer(data=request_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def save_data(self, serializer, validated_data):
        validated_data = validated_data
        name = validated_data["name"]
        attributes_json = validated_data.get("attributes")
        attributes = attributes_json and json.loads(attributes_json) or None

        if serializer.is_valid():
            product = serializer.save(user=self.request.user)

            """Save attributes of products"""
            for attribute in attributes:
                try:
                    attribute_value = ProductAttributeValues.objects.get(
                        product=product.id, attributevalues=attribute
                    )
                except ProductAttributeValues.DoesNotExist:
                    attr_data = {}
                    attr_data["product"] = product.id
                    attr_data["attributevalues"] = attribute
                    attr = ProductAttributeValuesSerializer(data=attr_data)
                    if attr.is_valid():
                        attr.save()
                    else:
                        return Response(attr.errors, status=status.HTTP_400_BAD_REQUEST)

            if self.action == "update":
                ProductAttributeValues.objects.filter(product=product.id).exclude(
                    attributevalues__in=attributes
                ).delete()

            images = self.request.FILES

            try:
                default_activity_img_exsts = Media.objects.get(
                    product=product.id, default=True
                )
            except Media.DoesNotExist:
                default_activity_img_exsts = False

            flag = 1
            if default_activity_img_exsts:
                default_set = True
            else:
                default_set = False

            arr = []

            for img_name in images:
                modified_data = {}
                modified_data["product"] = product.id
                modified_data["alt_text"] = name
                modified_data["image"] = images[img_name]
                modified_data["thumbnail"] = images[img_name]
                modified_data["small_image"] = images[img_name]
                if not default_set:
                    modified_data["default"] = True
                    default_set = True
                else:
                    modified_data["default"] = False
                file_serializer = ProductImageSerializer(data=modified_data)
                if file_serializer.is_valid():
                    file = file_serializer.save()
                    arr.append(file_serializer.data)
                else:
                    flag = 0

            if flag == 0:
                return Response(arr, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        """Create a new product"""

        validated_data = self.request.data
        self.save_data(serializer=serializer, validated_data=validated_data)

    def get_attributes(self, queryset):
        # Get related attributes
        p_a_v = "productattributevaluess__attributevalues__attribute_value"
        p_a_id = "productattributevaluess__attributevalues__id"
        p_a_p_id = "productattributevaluess__attributevalues__product_attribute__id"
        p_a_p_n = "productattributevaluess__attributevalues__product_attribute__name"
        queryset2 = queryset.filter(
            productattributevaluess__attributevalues__isnull=False
        ).values(
            "id",
            "name",
            p_a_p_id,
            p_a_p_n,
            p_a_id,
            p_a_v,
        )

        attributes = []
        for attribute in queryset2:
            attribute_exits = any(x["id"] == attribute[p_a_p_id] for x in attributes)

            if attribute_exits:
                for val in attributes:
                    if val["id"] == attribute[p_a_p_id]:
                        attribute_exits = any(
                            x["id"] == attribute[p_a_id] for x in val["values"]
                        )
                        if attribute_exits:
                            continue
                        else:
                            value_data = {}
                            value_data["id"] = attribute[p_a_id]
                            value_data["name"] = attribute[p_a_v]
                            value_data["product_count"] = sum(
                                p[p_a_v] == value_data["name"] for p in queryset2
                            )

                            val["values"].append(value_data)
                        # break
            else:
                data = {}
                data["id"] = attribute[p_a_p_id]
                data["name"] = attribute[p_a_p_n]
                data["values"] = []
                value_data = {}
                value_data["id"] = attribute[p_a_id]
                value_data["name"] = attribute[p_a_v]
                value_data["product_count"] = sum(
                    p[p_a_v] == value_data["name"] for p in queryset2
                )

                data["values"].append(value_data)
                attributes.append(data)
        return attributes

    @action(
        methods=["POST"],
        detail=False,
        url_path="product-search",
        permission_classes=[permissions.allowAny],
    )
    def product_search(self, request, *args, **kwargs):
        """Get products with applied filters, search & others"""
        queryset = self.filter_queryset(self.get_queryset())
        filterData = request.data
        appliedFilters = filterData.get("filters") or []

        for item in appliedFilters:
            queryset = queryset.filter(attribute_values__in=item["selected"])

        attributes = self.get_attributes(queryset)
        response_data = {}
        response_data["attributes"] = attributes

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)

            response = self.get_paginated_response(serializer.data)
            response.data["attributes"] = attributes

            return Response(data=response.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(queryset, many=True)
        response_data["items"] = serializer.data
        return Response(response_data)

    @action(methods=["DELETE"], detail=False, url_path="images/(?P<image_id>\d+)")
    def delete_image(self, request, image_id):
        """Get attributes related to category"""

        try:
            instance = Media.objects.get(id=image_id)

            if instance.product.user.id != request.user.id:
                return Response("Unauthorised", status=status.HTTP_401_UNAUTHORIZED)
            if instance.default:
                return Response(
                    "Cannot delete a default image", status=status.HTTP_400_BAD_REQUEST
                )
            else:
                instance.delete()
                return Response(
                    "Image deleted successfully", status=status.HTTP_204_NO_CONTENT
                )
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=["PUT"], detail=False, url_path="images/(?P<image_id>\d+)/make-default"
    )
    def make_default(self, request, image_id):
        """Make a product image default"""

        try:
            product_image = Media.objects.get(id=image_id)
            if product_image.product.user.id != request.user.id:
                return Response("Unauthorised", status=status.HTTP_401_UNAUTHORIZED)
            if product_image.default:
                return Response(
                    "Image is already marked default",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_image = product_image
            new_image.default = True

            Media.objects.filter(product=product_image.product, default=True).update(
                default=False
            )

            new_image.save()
            return Response("Default product image changed", status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        dataSet = serializer.data
        attributes_unsorted = dataSet["attribute_values"]

        dataSet["attributes"] = []
        for attribute in attributes_unsorted:
            attribute_exits = any(
                x["name"] == attribute["product_attribute"]
                for x in dataSet["attributes"]
            )

            if attribute_exits:
                for val in dataSet["attributes"]:
                    if val["name"] == attribute["product_attribute"]:
                        attribute_exits = any(
                            x["id"] == attribute["id"] for x in val["values"]
                        )
                        if attribute_exits:
                            continue
                        else:
                            value_data = {}
                            value_data["id"] = attribute["id"]
                            value_data["name"] = attribute["attribute_value"]
                            val["values"].append(value_data)

            else:
                atrribute_single = {}
                atrribute_single["name"] = attribute["product_attribute"]
                try:
                    product_attr_data = ProductAttribute.objects.get(
                        name=attribute["product_attribute"], is_color=True
                    )
                    if product_attr_data:
                        atrribute_single["is_color"] = True
                except ProductAttribute.DoesNotExist:
                    atrribute_single["is_color"] = False
                try:
                    product_attr_data = ProductAttribute.objects.get(
                        name=attribute["product_attribute"], is_size=True
                    )
                    if product_attr_data:
                        atrribute_single["is_size"] = True
                except ProductAttribute.DoesNotExist:
                    atrribute_single["is_size"] = False
                atrribute_single["values"] = []

                value_data = {}
                value_data["id"] = attribute["id"]
                value_data["name"] = attribute["attribute_value"]
                atrribute_single["values"].append(value_data)

                dataSet["attributes"].append(atrribute_single)

        dataSet.pop("attribute_values", None)
        return Response(dataSet)

    @action(methods=["GET"], detail=False, url_path="user/(?P<user_id>\d+)")
    def retrieve_user_products(self, request, user_id):
        filterData = self.request.query_params
        # Get query params
        is_active = filterData.get("is_active") or None

        queryset = self.filter_queryset(self.get_queryset())
        user = self.request.user
        user_id = int(user_id)
        if user.is_authenticated and user.is_professional and user_id == user.id:
            queryset = Product.objects.filter(user__id=user.id).order_by("-id")
        else:
            queryset = Product.objects.filter(
                Q(user__id=user_id, is_active=True)
            ).order_by("-id")

        if is_active != None:
            is_active_int = int(is_active)
            if is_active_int > 1:
                is_active_int = 1
            queryset = queryset.filter(is_active=is_active_int)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CreateBidView(generics.ListCreateAPIView):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]


    def create(self, request, *args, **kwargs):
        auction_id = request.data.get('auction')
        bid_amount = int(request.data.get('bid_amount'))
        auction = Product.objects.get(pk=auction_id)
        current_time = timezone.now()
        auction_start_time = auction.start_time
        auction_end_time = auction.end_time

        if auction_start_time < current_time and auction_end_time > current_time and auction_start_time < auction_end_time:
            try:
                auction = Product.objects.get(pk=auction_id)
            except Product.DoesNotExist:
                return Response({"detail": "Auction not found."}, status=status.HTTP_404_NOT_FOUND)

            if auction.current_highest_bid is None or auction.current_highest_bid == 0 or bid_amount > (auction.current_highest_bid + auction.bidding_step):
                auction.current_highest_bid = bid_amount
            else:
                return Response({"detail": "Bid amount must be greater than the current highest bid amount"}, status=status.HTTP_400_BAD_REQUEST)

            # Create a Bid object but do not save it yet
            bid = Bid(auction=auction, bidder=request.user, bid_amount=bid_amount)

            if self.perform_create(bid):
                return Response({"detail": "Bid placed successfully."}, status=status.HTTP_201_CREATED)
            else:
                return Response({"detail": "Failed to place bid."}, status=status.HTTP_400_BAD_REQUEST)

        else:
                return Response({"detail": "Bid can only be placed within the specified time frame."}, status=status.HTTP_400_BAD_REQUEST)
        
 
    def perform_create(self, bid):
 
        try:
            bid.save()
            bid.auction.save()
            return True
        except Exception:
            return False
        

class AuctionBidListView(generics.ListAPIView):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    filter_backends = [filters.SearchFilter]
    search_fields = ['auction__id']  # Filter by auction ID

    def get_queryset(self):
        return Bid.objects.filter(auction__id=self.kwargs['auction_id'])


class BidListView(generics.ListAPIView):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication] 


class BidRetrieveView(generics.RetrieveAPIView):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    lookup_url_kwarg = 'pk'

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return self.get_success_response(serializer.data)
        except NotFound:
            return self.get_not_found_response()

    def get_success_response(self, data):
        return Response(data)

    def get_not_found_response(self):
        return Response({"detail": "Bid not found."}, status=status.HTTP_404_NOT_FOUND)
    

class RecordView(generics.CreateAPIView):
    queryset = UserStats.objects.all()
    serializer_class = UserStatsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def perform_create(self, serializer):
        user = self.request.user
        auction_id = self.request.data.get('auction')
        auction = get_object_or_404(Product, id=auction_id)

        # Check if a view already exists for this user and auction within the last 24 hours
        one_day_ago = timezone.now() - timedelta(days=1)
        existing_view = UserStats.objects.filter(user=user, auction=auction).first()

        if not existing_view:
            # Record a new view
            serializer.save(user=user, auction=auction)


class GetAllViewRecords(generics.ListAPIView):
    serializer_class = UserStatsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        user = self.request.user
        time_frame = self.request.data.get('time_frame')
        if time_frame == '1week':
            one_week_ago = timezone.now() - timedelta(weeks=1)
            queryset = UserStats.objects.filter(auction__user=user, view_timestamp__gte=one_week_ago)
            return queryset
        elif time_frame == '1month':
            one_month_ago = timezone.now() - timedelta(days=30)
            queryset = UserStats.objects.filter(auction__user=user, view_timestamp__gte=one_month_ago)
            return queryset
        elif time_frame == '6months':
            six_months_ago = timezone.now() - timedelta(days=180)
            queryset = UserStats.objects.filter(auction__user=user, view_timestamp__gte=six_months_ago)
            return queryset
        else:
            return UserStats.objects.none()
        
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        bid_count = queryset.count()
        return Response({'total_views': bid_count}, status=status.HTTP_200_OK)


class GetUserTotalBids(generics.ListAPIView):
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated, permissions.IsAuctionOwner]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        user = self.request.user
        time_frame = self.request.data.get('time_frame')

        if time_frame == '1week':
            one_week_ago = timezone.now() - timedelta(weeks=1)
            return Bid.objects.filter(auction__user=user, bid_time__gte=one_week_ago)
        elif time_frame == '1month':
            one_month_ago = timezone.now() - timedelta(days=30)
            return Bid.objects.filter(auction__user=user, bid_time__gte=one_month_ago)
        elif time_frame == '6months':
            six_months_ago = timezone.now() - timedelta(days=180)
            return Bid.objects.filter(auction__user=user, bid_time__gte=six_months_ago)
        else:
            return Bid.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        bid_count = queryset.count()
        return Response({'total_bids': bid_count}, status=status.HTTP_200_OK)


class BidChartView(generics.ListAPIView):
    serializer_class = BidChartSerializer
    permission_classes = [IsAuthenticated, permissions.IsAuctionOwner]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        user = self.request.user
        bid_data = (
            Bid.objects
            .filter(auction__user=user)
            .values('bid_time__date')
            .annotate(bid_count=Count('id'))
            # .order_by('bid_time__date')
        )

        return bid_data
    

class ViewChartView(generics.ListAPIView):
    serializer_class = ViewChartSerializer
    permission_classes = [IsAuthenticated, permissions.IsAuctionOwner]
    authentication_classes = [TokenAuthentication]


    def get_queryset(self):
        # Retrieve view data with counts for each date
        user = self.request.user
        view_data = UserStats.objects.filter(auction__user=user).annotate(view_date=TruncDate('view_timestamp')).values('view_date').annotate(view_count=Count('id'))
        return view_data
    

def resize_image(uploaded_file, width, height):
    img = Image.open(uploaded_file)
    img.thumbnail((width, height))
    
    output_io = BytesIO()
    img.save(output_io, format='JPEG')
    
    # Create an InMemoryUploadedFile from the BytesIO
    return InMemoryUploadedFile(output_io, None, 'image.jpg', 'image/jpeg', output_io.tell(), None)


# Define the generate_unique_filename function outside the class
def generate_unique_filename(filename):
    # Get the file extension
    file_extension = os.path.splitext(filename)[-1]

    # Generate a random string (you can adjust the length as needed)
    random_string = str(uuid.uuid4().hex)[:8]

    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Combine the timestamp, random string, and file extension
    unique_filename = f"{timestamp}_{random_string}{file_extension}"

    return unique_filename


def create_resized_image(uploaded_file, width, height):
    image = Image.open(uploaded_file)
    image = image.resize((width, height), Image.ANTIALIAS)

    # Create an in-memory file-like object (BytesIO) to hold the resized image
    output = BytesIO()
    image.save(output, format='JPEG')
    output.seek(0)  # Reset the stream to the beginning

    return output


def upload_image_to_firebase(file, location, width, height):
    unique_filename = generate_unique_filename(file.name)
    resized_image = create_resized_image(file, width, height)

    # Initialize the Firebase Storage client
    bucket = storage.bucket()
    file_name = f'product/{location}/{unique_filename}'

    # Upload the resized image to Firebase Storage
    blob = bucket.blob(file_name)
    blob.upload_from_file(resized_image, content_type='image/jpeg')

    # Get the public URL of the uploaded file
    file_url = blob.public_url
    return file_name

class FileUploadView(generics.CreateAPIView):
    queryset = ProductImages.objects.all()
    serializer_class = FileUploadSerializer

    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        product_id = request.data.get('product')

        if not uploaded_file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_400_BAD_REQUEST)


        unique_filename = generate_unique_filename(uploaded_file.name)

        # Resize the uploaded image
        resized_image = create_resized_image(uploaded_file, 600, 600)

        # Initialize the Firebase Storage client
        bucket = storage.bucket()
        file_name = f'uploads/{unique_filename}'

        # Upload the resized image to Firebase Storage
        blob = bucket.blob(file_name)
        blob.upload_from_file(resized_image, content_type='image/jpeg')

        # Get the public URL of the uploaded file
        file_url = blob.public_url

        data = {
            'product': product.id,
            'url': file_url,
        }

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer, product, unique_filename)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer, product, unique_filename):
        serializer.save(product=product, url=unique_filename)



class ImageUploadView(generics.CreateAPIView):
    serializer_class = ProductMediaSerializer

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        product = get_object_or_404(Product, pk=product_id)
        main_pic = request.FILES.get('main_picture')
        images = request.FILES.getlist('other_pictures')

        if not main_pic and not images:
            return Response({'error': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)

        product_media = ProductMedia(product=product)

        if main_pic:
            product_media.main_picture = generate_unique_filename(main_pic.name)
            product_media.thumbnail = generate_unique_filename(main_pic.name)

        product_media.save()

        # Create and save instances for other pictures
        for uploaded_file in images:
            product_image = ProductImages(product=product, image=generate_unique_filename(uploaded_file.name))
            product_image.save()

        # Upload images to Firebase Storage
        if main_pic:
            upload_image_to_firebase(main_pic, 'picture', 600, 600)
            upload_image_to_firebase(main_pic, 'thumbnails', 300, 300)

        for uploaded_file in images:            
            upload_image_to_firebase(uploaded_file, 'images', 600, 600)

        serializer = self.get_serializer(product_media)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



class AccessTokenView(generics.RetrieveAPIView):
    queryset = ProductImages.objects.all()
    serializer_class = ImageSerializer


    def get_object(self):
        # image_name = self.request.query_params.get('image_name')
        product_id = self.request.query_params.get('product')
        image = ProductImages.objects.get(product_id=product_id)
        image_name = image.url

        image_path = f'uploads/{image_name}'

        try:
            url = f'https://firebasestorage.googleapis.com/v0/b/auction-c5969.appspot.com/o/uploads%2F{image_name}'

            # Send the GET request
            response = requests.get(url)

            # Check if the request was successful (status code 200)
            if response.status_code == 200:

                # Print the response content
                # print(response.text)
                return response.json(), image_name
            
            else:
                return f'Error: {response.status_code}'

        except Exception as e:
            return None

    def retrieve(self, request, *args, **kwargs):
        access_token = self.get_object()
        if access_token is not None:
            return Response({
                'access_token': f'https://firebasestorage.googleapis.com/v0/b/auction-c5969.appspot.com/o/uploads%2F{access_token[1]}?alt=media&token={access_token[0]["downloadTokens"]}'
            })            
        else:
            return Response({'error': 'Image not found.'}, status=404)