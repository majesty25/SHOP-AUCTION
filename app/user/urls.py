from django.urls import include, path
from rest_framework.routers import DefaultRouter

from user import views

router = DefaultRouter()
router.register(
    "admin-users-non-pro", views.AdminNonProUsersViewSet, basename="adminnonprousers"
)
router.register("manage-admins", views.ManageAdminUserViewSet, basename="manageadmins")

app_name = "user"

urlpatterns = [
    path("", include(router.urls)),
    path("hello/", views.hello_world, name="hello"),
    path("create/", views.CreateUserView.as_view(), name="create"),
    # path("create-super/", views.CreateUserView.as_view(), name="create"),

    path("token/", views.CreateTokenView.as_view(), name="token"),
    path("me/", views.ManageUserView.as_view(), name="me"),
    path(
        "user-image/<int:pk>",
        views.UserImageViewset.as_view(),
        name="user-upload-image",
    ),
    path("password-reset/", views.password_reset, name="password-reset"),
    path(
        "password-reset-verify/",
        views.password_reset_verify,
        name="password-reset-verify",
    ),
    path(
        "password-reset-change/",
        views.password_reset_change,
        name="password-reset-change",
    ),
    path(
        "activate-deactivate-user/",
        views.activate_deactivate_user,
        name="activate-deactivate-user",
    ),
    path("validate-user-email/", views.validate_user_email, name="validate-user-email"),
    path("validate-user-phone/", views.validate_user_phone, name="validate-user-phone"),
]
