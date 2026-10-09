
from unittest.mock import patch
from django.db import IntegrityError
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from collabdoc.models import Document, DocumentVersion

user = User.objects.get(username="collabdocs_demo_owner")
client = APIClient()
client.force_authenticate(user=user)

doc = Document.objects.get(
    id="09b20a7e-4785-453f-8aa3-3ab6b36f0a82"
)

original_title = doc.title
original_version_count = DocumentVersion.objects.filter(
    document=doc
).count()

with patch.object(
    DocumentVersion.objects,
    "create",
    side_effect=IntegrityError("Intentional version failure"),
):
    response = client.patch(
        f"/api/documents/{doc.id}/",
        {"title": "ROLLBACK_TEST_TITLE"},
        format="json",
    )

doc.refresh_from_db()
current_version_count = DocumentVersion.objects.filter(
    document=doc
).count()

print("HTTP status:", response.status_code)
print("Original title preserved:", doc.title == original_title)
print("Version count unchanged:", current_version_count == original_version_count)
