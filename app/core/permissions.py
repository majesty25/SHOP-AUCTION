from rest_framework import permissions


class allowSafeMethods(permissions.BasePermission):
    """Allow only super user to unsafe methods"""

    def has_permission(self, request, view):
        """Check if user is trying to acces safe methods"""
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user and request.user.is_authenticated and request.user.is_superuser
        )


class allowSafeMethodsToNonStaff(permissions.BasePermission):
    """Allow only super user to unsafe methods"""

    def has_permission(self, request, view):
        """Check if user is trying to acces safe methods"""
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff


class allowAny(permissions.BasePermission):
    """Allow any methods"""

    def has_permission(self, request, view):
        """Check if user is trying to acces safe methods"""
        if request.method:
            return True


class allowPostMethodOnly(permissions.BasePermission):
    """Allow only super user to unsafe methods"""

    def has_permission(self, request, view):
        """Check if user is trying to acces post method"""
        if request.method == "POST":
            return True
        return False


class UpdateOwnStatus(permissions.BasePermission):
    """Allow users to update their own status"""

    def has_object_permission(self, request, view, obj):
        """Check if user is trying to update own status"""
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user_profile.id == request.user.id


class UpdateOwnObject(permissions.BasePermission):
    """Allow users to update their own objects"""

    def has_object_permission(self, request, view, obj):
        """Check if user is trying to update own object"""
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user.id == request.user.id


class allowNonDefaultImages(permissions.BasePermission):
    """Allow delete of only non default images"""

    def has_object_permission(self, request, view, obj):
        """Check if user is trying to update own status"""
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.default != True


class IsNotAuthenticated(permissions.BasePermission):
    """
    Allows access only to non authenticated users.
    """

    def has_permission(self, request, view):
        return not request.user.is_authenticated()


class allowOnlyAuthenticatedAdmins(permissions.BasePermission):
    """Allow only authenticated admin to methods"""

    def has_permission(self, request, view):
        """Check if user is an admin"""
        return request.user and request.user.is_authenticated and request.user.is_staff


class allowOnlyAuthenticatedSuperAdmins(permissions.BasePermission):
    """Allow only authenticated super admin to methods"""

    def has_permission(self, request, view):
        """Check if user is a super admin"""
        return (
            request.user and request.user.is_authenticated and request.user.is_superuser
        )



class IsAuctionOwner(permissions.BasePermission):
    """
    Custom permission to check if the user is the owner of the auction.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the user is the owner of the auction
        return obj.auction.owner == request.user
