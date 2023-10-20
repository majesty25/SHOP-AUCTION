import json
from html import unescape
from itertools import product

from django.contrib.postgres.search import SearchVector
from django.db.models import Count, Q
from rest_framework import (authentication, mixins, serializers, status,
                            viewsets)
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import (action, api_view,
                                       authentication_classes,
                                       permission_classes)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core import permissions
from core.utils import (StandardResultsSetPagination, clean_url,
                        create_error_data, create_message_data)
from shop.models import Category
from shop.serializers import CategorySerializer


@api_view(["GET"])
def get_app_data(request):
    """Get app data and settings"""
    data = {}
    settings = {
        "headerHeadline1": "New Styles",
        "headerButtonText": "Read more",
    }
    data["settings"] = settings

    return Response(data=data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_location_data(request):
    """Get app data and settings"""
    data = {}

    json_data = open('cities.json')   
    data1 = json.load(json_data)

    data["location"] = data1

    return Response(data=data, status=status.HTTP_200_OK)


# admin views
class ShopCategoryViewSetAdmin(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
):
    """Manages shop categories in database"""

    serializer_class = CategorySerializer
    queryset = Category.objects.filter(level=0)
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.allowOnlyAuthenticatedAdmins,)
