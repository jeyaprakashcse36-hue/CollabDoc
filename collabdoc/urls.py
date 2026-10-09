from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogViewSet,
    CommentViewSet,
    DocumentViewSet,
    TagViewSet,
    UserViewSet,
    WorkspaceMemberViewSet,
    WorkspaceViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("workspaces", WorkspaceViewSet, basename="workspace")
router.register(
    r"workspaces/(?P<workspace_pk>[^/.]+)/members",
    WorkspaceMemberViewSet,
    basename="workspace-member",
)
router.register("documents", DocumentViewSet, basename="document")
router.register("tags", TagViewSet, basename="tag")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    *router.urls,
    path(
        "documents/<uuid:document_pk>/comments/",
        CommentViewSet.as_view({"get": "list", "post": "create"}),
        name="document-comments",
    ),
    path(
        "documents/<uuid:document_pk>/comments/<uuid:pk>/",
        CommentViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="document-comment-detail",
    ),
]
