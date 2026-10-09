from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AuditLog, Document, DocumentVersion, Workspace, WorkspaceMember


class CollabDocsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="test_owner",
            password="TestPassword123!",
        )
        self.client.force_authenticate(user=self.owner)

    def test_workspace_creation_adds_owner_as_admin(self):
        response = self.client.post(
            "/api/workspaces/",
            {"name": "Test Workspace", "description": "API test"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        workspace = Workspace.objects.get(pk=response.data["id"])
        membership = WorkspaceMember.objects.get(workspace=workspace, user=self.owner)
        self.assertEqual(membership.role, WorkspaceMember.Role.ADMIN)

    def test_document_create_and_update_create_versions_and_audit_logs(self):
        workspace_response = self.client.post(
            "/api/workspaces/",
            {"name": "Version Test Workspace"},
            format="json",
        )
        workspace_id = workspace_response.data["id"]
        create_response = self.client.post(
            "/api/documents/",
            {
                "workspace": workspace_id,
                "title": "Versioned document",
                "content": "Version one",
                "status": "draft",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        document_id = create_response.data["id"]
        self.assertEqual(DocumentVersion.objects.filter(document_id=document_id).count(), 1)
        self.assertTrue(AuditLog.objects.filter(object_id=document_id, action="DOCUMENT_CREATED").exists())

        update_response = self.client.patch(
            f"/api/documents/{document_id}/",
            {"content": "Version two"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(DocumentVersion.objects.filter(document_id=document_id).count(), 2)
        self.assertTrue(AuditLog.objects.filter(object_id=document_id, action="DOCUMENT_UPDATED").exists())

    def test_duplicate_workspace_membership_returns_conflict(self):
        workspace_response = self.client.post(
            "/api/workspaces/",
            {"name": "Membership Test Workspace"},
            format="json",
        )
        workspace_id = workspace_response.data["id"]
        collaborator = User.objects.create_user(
            username="test_collaborator",
            password="TestPassword123!",
        )
        payload = {"user": collaborator.pk, "role": "editor"}
        first = self.client.post(
            f"/api/workspaces/{workspace_id}/members/", payload, format="json"
        )
        second = self.client.post(
            f"/api/workspaces/{workspace_id}/members/", payload, format="json"
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
