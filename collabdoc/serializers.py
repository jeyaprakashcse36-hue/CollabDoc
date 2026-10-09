from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    AuditLog,
    Comment,
    Document,
    DocumentVersion,
    Tag,
    Workspace,
    WorkspaceMember,
)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=8,
    )
    workspace_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "workspace_count",
        ]
        read_only_fields = ["id", "workspace_count"]

    def get_workspace_count(self, obj):
        return obj.workspace_memberships.count()

    def validate_username(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Username cannot be empty."
            )

        if User.objects.filter(
            username__iexact=value
        ).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )

        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must contain at least 8 characters."
            )

        return value


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = WorkspaceMember
        fields = [
            "id",
            "workspace",
            "user",
            "username",
            "role",
            "joined_at",
        ]
        read_only_fields = [
            "id",
            "joined_at",
            "username",
        ]

    def validate(self, attrs):
        workspace = attrs.get(
            "workspace",
            self.instance.workspace if self.instance else None,
        )
        user = attrs.get(
            "user",
            self.instance.user if self.instance else None,
        )

        if workspace and not workspace.is_active:
            raise serializers.ValidationError(
                {
                    "workspace": (
                        "Cannot add members to an inactive workspace."
                    )
                }
            )

        if workspace and user:
            existing = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=user,
            )

            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise serializers.ValidationError(
                    {
                        "user": (
                            "This user is already a member "
                            "of this workspace."
                        )
                    }
                )

        return attrs


class WorkspaceSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True,
    )
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "owner_username",
            "is_active",
            "created_at",
            "updated_at",
            "member_count",
        ]
        read_only_fields = [
            "id",
            "owner",
            "owner_username",
            "is_active",
            "created_at",
            "updated_at",
            "member_count",
        ]

    def get_member_count(self, obj):
        return getattr(obj, "_member_count", obj.members.count())

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Workspace name cannot be empty."
            )

        if len(value) < 3:
            raise serializers.ValidationError(
                "Workspace name must be at least 3 characters long."
            )

        return value


class DocumentVersionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "document",
            "version_number",
            "title",
            "content",
            "created_by",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "version_number",
            "created_by",
            "created_by_username",
            "created_at",
        ]


class TagSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "document_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "document_count",
            "created_at",
        ]

    def get_document_count(self, obj):
        return getattr(obj, "_document_count", obj.documents.count())

    def validate_name(self, value):
        value = value.strip().lower()

        if not value:
            raise serializers.ValidationError(
                "Tag name cannot be empty."
            )

        if len(value) > 100:
            raise serializers.ValidationError(
                "Tag name cannot exceed 100 characters."
            )

        return value


class DocumentSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )
    workspace_name = serializers.CharField(
        source="workspace.name",
        read_only=True,
    )
    version_count = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        source="tags",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "title",
            "content",
            "status",
            "created_by",
            "created_by_username",
            "version_count",
            "tags",
            "tag_ids",
            "created_at",
            "updated_at",
            "comment_count",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_by_username",
            "workspace_name",
            "version_count",
            "comment_count",
            "created_at",
            "updated_at",
        ]

    def get_version_count(self, obj):
        return getattr(obj, "_version_count", obj.versions.count())

    comment_count = serializers.SerializerMethodField()

    def get_comment_count(self, obj):
        return getattr(obj, "_comment_count", obj.comments.count())

    def validate(self, attrs):
        title = attrs.get(
            "title",
            self.instance.title if self.instance else "",
        )

        if not title.strip():
            raise serializers.ValidationError(
                {"title": "Document title cannot be empty."}
            )

        workspace = attrs.get(
            "workspace",
            self.instance.workspace if self.instance else None,
        )

        if workspace and not workspace.is_active:
            raise serializers.ValidationError(
                {
                    "workspace": (
                        "Documents cannot be created or updated "
                        "in an inactive workspace."
                    )
                }
            )

        return attrs
    def create(self, validated_data):
        tags = validated_data.pop("tags", [])

        request = self.context.get("request")

        document = Document(**validated_data)

        if request and request.user.is_authenticated:
            document._actor = request.user

        document.save()

        if tags:
            document.tags.set(tags)

        return document


    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        request = self.context.get("request")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if request and request.user.is_authenticated:
            instance._actor = request.user

        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        return instance


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "document",
            "user",
            "username",
            "content",
            "parent",
            "reply_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "username",
            "reply_count",
            "created_at",
            "updated_at",
        ]

    def get_reply_count(self, obj):
        return obj.replies.count()

    def validate_content(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Comment content cannot be empty."
            )

        return value

    def validate(self, attrs):
        document = attrs.get(
            "document",
            self.instance.document if self.instance else None,
        )
        parent = attrs.get("parent")

        if parent and document and parent.document_id != document.id:
            raise serializers.ValidationError(
                {
                    "parent": (
                        "Parent comment must belong to the same document."
                    )
                }
            )

        if parent and self.instance and parent.pk == self.instance.pk:
            raise serializers.ValidationError(
                {"parent": "A comment cannot be its own parent."}
            )

        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(
        source="actor.username",
        read_only=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_username",
            "action",
            "model_name",
            "object_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "actor_username",
            "created_at",
        ]
