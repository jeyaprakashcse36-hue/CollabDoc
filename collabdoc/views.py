from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    AuditLog,
    Comment,
    Document,
    DocumentVersion,
    Tag,
    Workspace,
    WorkspaceMember,
)
from .permission import IsWorkspaceAdmin, IsWorkspaceEditorOrAdmin, IsWorkspaceMember
from .permissions import IsAdminUser
from .serializers import (
    AuditLogSerializer,
    CommentSerializer,
    DocumentSerializer,
    DocumentVersionSerializer,
    TagSerializer,
    UserSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        if self.request.user.is_staff or self.request.user.is_superuser:
            return User.objects.all().order_by("id")
        return User.objects.filter(pk=self.request.user.pk)

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get("password")
        if not password:
            return Response(
                {"password": ["This field is required for registration."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=serializer.validated_data["username"],
            email=serializer.validated_data.get("email", ""),
            password=password,
            first_name=serializer.validated_data.get("first_name", ""),
            last_name=serializer.validated_data.get("last_name", ""),
        )

        output = self.get_serializer(user)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Workspace.objects
            .filter(members__user=self.request.user)
            .select_related("owner")
            .prefetch_related("members__user")
            .annotate(_member_count=Count("members", distinct=True))
            .distinct()
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                workspace = Workspace.objects.create(
                    name=serializer.validated_data["name"],
                    description=serializer.validated_data.get(
                        "description",
                        "",
                    ),
                    owner=request.user,
                )

                WorkspaceMember.objects.create(
                    workspace=workspace,
                    user=request.user,
                    role=WorkspaceMember.Role.ADMIN,
                )

        except IntegrityError:
            return Response(
                {
                    "message": (
                        "Unable to create workspace because "
                        "the owner membership could not be created."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        output = self.get_serializer(workspace)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        workspace = self.get_object()

        if not WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role=WorkspaceMember.Role.ADMIN,
        ).exists():
            return Response(
                {
                    "message": (
                        "Only workspace administrators "
                        "can update a workspace."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        workspace = self.get_object()

        if not WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role=WorkspaceMember.Role.ADMIN,
        ).exists():
            return Response(
                {
                    "message": (
                        "Only workspace administrators "
                        "can delete a workspace."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]

        return super().get_permissions()


class WorkspaceMemberViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        workspace_id = self.kwargs.get("workspace_pk")

        return (
            WorkspaceMember.objects
            .filter(
                workspace_id=workspace_id,
                workspace__members__user=self.request.user,
            )
            .select_related("user", "workspace")
        )

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsWorkspaceAdmin()]
        return [IsAuthenticated(), IsWorkspaceMember()]

    def update(self, request, *args, **kwargs):
        membership = self.get_object()
        if not WorkspaceMember.objects.filter(
            workspace=membership.workspace,
            user=request.user,
            role=WorkspaceMember.Role.ADMIN,
        ).exists():
            return Response({"message": "Only workspace administrators can update membership."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        membership = self.get_object()
        if not WorkspaceMember.objects.filter(
            workspace=membership.workspace,
            user=request.user,
            role=WorkspaceMember.Role.ADMIN,
        ).exists():
            return Response({"message": "Only workspace administrators can remove members."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        workspace_id = kwargs.get("workspace_pk")

        try:
            workspace = Workspace.objects.get(
                pk=workspace_id,
                is_active=True,
            )
        except Workspace.DoesNotExist:
            return Response(
                {
                    "message": "Workspace not found or inactive."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role=WorkspaceMember.Role.ADMIN,
        ).exists()

        if not is_admin:
            return Response(
                {
                    "message": (
                        "Only workspace administrators "
                        "can add members."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        requested_user_id = request.data.get("user")
        if requested_user_id and WorkspaceMember.objects.filter(
            workspace=workspace,
            user_id=requested_user_id,
        ).exists():
            return Response(
                {"message": "This user is already a member of the workspace."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = self.get_serializer(
            data={
                **request.data,
                "workspace": workspace.id,
            }
        )
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                member = WorkspaceMember.objects.create(
                    workspace=workspace,
                    user=serializer.validated_data["user"],
                    role=serializer.validated_data["role"],
                )
        except IntegrityError:
            return Response(
                {
                    "message": (
                        "This user is already a member "
                        "of the workspace."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        output = self.get_serializer(member)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        
        queryset = (
            Document.objects
            .filter(workspace__members__user=self.request.user)
            .select_related("workspace", "created_by")
            .prefetch_related("tags")
            .distinct()
            .annotate(
                _version_count=Count("versions", distinct=True),
                _comment_count=Count("comments", distinct=True),)
        )

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search)
            )

        status_param = self.request.query_params.get("status")
        if status_param:
            statuses = [
                value.strip()
                for value in status_param.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(status__in=statuses)

        created_from = self.request.query_params.get("created_from")
        if created_from:
            queryset = queryset.filter(created_at__date__gte=created_from)

        created_to = self.request.query_params.get("created_to")
        if created_to:
            queryset = queryset.filter(created_at__date__lte=created_to)

        workspace_ids = self.request.query_params.get("workspace_ids")
        if workspace_ids:
            requested_ids = [value.strip() for value in workspace_ids.split(",") if value.strip()]
            allowed_ids = Workspace.objects.filter(
                members__user=self.request.user,
                id__in=requested_ids,
            ).values_list("id", flat=True)
            queryset = queryset.filter(workspace_id__in=allowed_ids)

        return queryset

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            return [IsAuthenticated(), IsWorkspaceEditorOrAdmin()]

        if self.action == "destroy":
            return [IsAuthenticated(), IsWorkspaceAdmin()]

        return [IsAuthenticated(), IsWorkspaceMember()]

    def create(self, request, *args, **kwargs):
        workspace_id = request.data.get("workspace")

        if not workspace_id:
            return Response(
                {"message": "workspace is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            workspace = Workspace.objects.get(
                pk=workspace_id,
                is_active=True,
            )
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_editor_or_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[
                WorkspaceMember.Role.ADMIN,
                WorkspaceMember.Role.EDITOR,
            ],
        ).exists()

        if not is_editor_or_admin:
            return Response(
                {
                    "message": (
                        "Only workspace editors or administrators "
                        "can create documents."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                document = serializer.save(
                    created_by=request.user,
                )

                version_number = document.versions.count() + 1

                DocumentVersion.objects.create(
                    document=document,
                    version_number=version_number,
                    title=document.title,
                    content=document.content,
                    created_by=request.user,
                )

        except IntegrityError:
            return Response(
                {
                    "message": (
                        "Unable to create document because "
                        "a database constraint was violated."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        output = self.get_serializer(document)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        document = self.get_object()

        serializer = self.get_serializer(
            document,
            data=request.data,
            partial=kwargs.get("partial", False),
        )
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                document = serializer.save()

                version_number = document.versions.count() + 1

                DocumentVersion.objects.create(
                    document=document,
                    version_number=version_number,
                    title=document.title,
                    content=document.content,
                    created_by=request.user,
                )

        except IntegrityError:
            return Response(
                {
                    "message": (
                        "Unable to update document because "
                        "a database constraint was violated."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        output = self.get_serializer(document)

        return Response(output.data)
    @action(detail=True, methods=["get"], url_path="versions")
    def version_history(self, request, pk=None):
        document = self.get_object()

        versions = document.versions.select_related(
            "created_by"
        ).order_by("-version_number")

        serializer = DocumentVersionSerializer(
            versions,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)
    
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        document_id = self.kwargs.get("document_pk")

        return (
            Comment.objects
            .filter(
                document_id=document_id,
                document__workspace__members__user=self.request.user,
            )
            .select_related(
                "user",
                "document",
                "parent",
            )
            .distinct()
        )

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [
                IsAuthenticated(),
                IsWorkspaceEditorOrAdmin(),
            ]

        return [
            IsAuthenticated(),
            IsWorkspaceMember(),
        ]

    def create(self, request, *args, **kwargs):
        document_id = kwargs.get("document_pk")

        try:
            document = (
                Document.objects
                .select_related("workspace")
                .get(pk=document_id)
            )
        except Document.DoesNotExist:
            return Response(
                {"message": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_member = WorkspaceMember.objects.filter(
            workspace=document.workspace,
            user=request.user,
        ).exists()

        if not is_member:
            return Response(
                {"message": "You are not a member of this workspace."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_editor_or_admin = WorkspaceMember.objects.filter(
            workspace=document.workspace,
            user=request.user,
            role__in=[
                WorkspaceMember.Role.ADMIN,
                WorkspaceMember.Role.EDITOR,
            ],
        ).exists()

        if not is_editor_or_admin:
            return Response(
                {
                    "message": (
                        "Only workspace editors or administrators "
                        "can create comments."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.save(
            document=document,
            user=request.user,
        )

        return Response(
            self.get_serializer(comment).data,
            status=status.HTTP_201_CREATED,
        )
class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Tag.objects
            .annotate(_document_count=Count("documents", distinct=True))
            .order_by("name")
        )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tag = serializer.save()
        except IntegrityError:
            return Response(
                {"message": "A tag with this name already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            self.get_serializer(tag).data,
            status=status.HTTP_201_CREATED,
        )

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose audit records to Django staff users only."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = AuditLog.objects.select_related("actor").order_by("-created_at")
