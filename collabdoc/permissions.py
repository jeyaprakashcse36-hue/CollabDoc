from rest_framework.permissions import BasePermission

from .permission import (
    IsWorkspaceAdmin,
    IsWorkspaceEditorOrAdmin,
    IsWorkspaceMember,
)


class IsAdminUser(BasePermission):
    """Allow access only to authenticated Django staff/superuser accounts."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


__all__ = [
    "IsAdminUser",
    "IsWorkspaceAdmin",
    "IsWorkspaceEditorOrAdmin",
    "IsWorkspaceMember",
]
