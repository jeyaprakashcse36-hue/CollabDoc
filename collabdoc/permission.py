from rest_framework.permissions import BasePermission

from .models import WorkspaceMember


class IsWorkspaceMember(BasePermission):
    """
    Allows access only to users who belong to the workspace.
    """

    def has_object_permission(self, request, view, obj):
        workspace = self._get_workspace(obj)

        if workspace is None:
            return False

        return WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
        ).exists()

    def _get_workspace(self, obj):
        if hasattr(obj, "workspace"):
            return obj.workspace

        if hasattr(obj, "document"):
            return obj.document.workspace

        return None


class IsWorkspaceAdmin(BasePermission):
    """
    Allows access only to workspace administrators.
    """

    def has_object_permission(self, request, view, obj):
        workspace = self._get_workspace(obj)

        if workspace is None:
            return False

        return WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role=WorkspaceMember.Role.ADMIN,
        ).exists()

    def _get_workspace(self, obj):
        if hasattr(obj, "workspace"):
            return obj.workspace

        if hasattr(obj, "document"):
            return obj.document.workspace

        return None


class IsWorkspaceEditorOrAdmin(BasePermission):
    """
    Allows workspace admins and editors to modify content.
    """

    def has_object_permission(self, request, view, obj):
        workspace = self._get_workspace(obj)

        if workspace is None:
            return False

        return WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[
                WorkspaceMember.Role.ADMIN,
                WorkspaceMember.Role.EDITOR,
            ],
        ).exists()

    def _get_workspace(self, obj):
        if hasattr(obj, "workspace"):
            return obj.workspace

        if hasattr(obj, "document"):
            return obj.document.workspace

        return None