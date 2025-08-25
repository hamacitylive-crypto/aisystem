from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated and has the 'admin' role.
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )
