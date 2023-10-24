from django.urls import include, path
from rest_framework.routers import DefaultRouter

from shop.views import product_views, views

router = DefaultRouter()
router.register("category", product_views.ShopCategoryViewSet)
router.register("products", product_views.PublicProductViewSet)
router.register("productattributes", product_views.ProductAttributesViewSet)

app_name = "shop"

urlpatterns = [
    path("get-data", views.get_app_data, name="get-data"),
    path('bid/create/', product_views.CreateBidView.as_view(), name='bid-list'),
    path("location-data", views.get_location_data, name="location-data"),
    path('bids/list/', product_views.BidListView.as_view(), name='bid-list'),
    path('auction-bids/<int:auction_id>/', product_views.AuctionBidListView.as_view(), name='auction-bids'),
    path('bids/<int:pk>/', product_views.BidRetrieveView.as_view(), name='bid-detail'),
    path('record-view/', product_views.RecordView.as_view(), name='record_view'),
    path('view-records/', product_views.GetAllViewRecords.as_view(), name='get-all-view-records'),
    path('get-total-bids/', product_views.GetUserTotalBids.as_view(), name='get_total_bids'),
    path('bid-chart/', product_views.BidChartView.as_view(), name='bid-chart'),
    path('views-chart/', product_views.ViewChartView.as_view(), name='view-chart'),
    path('upload/', product_views.FileUploadView.as_view(), name='file-upload'),
    path('uploads/', product_views.ImageUploadView.as_view(), name='image-upload'),

    path('image/', product_views.AccessTokenView.as_view(), name='file-get'),
    path('images/', product_views.ImagesAccessTokenView.as_view(), name='files-get'),


    # path('delete-images/', views.delete_multiple_images, name='delete-images'),
    path("", include(router.urls)),
]
