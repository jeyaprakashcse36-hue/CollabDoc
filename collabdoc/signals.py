
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Document, AuditLog


@receiver(pre_save, sender=Document)
def capture_document_state(sender, instance, **kwargs):
    instance._was_adding = instance._state.adding


@receiver(post_save, sender=Document)
def document_audit_log(sender, instance, created, **kwargs):
    actor = getattr(instance, "_actor", None)

    action = (
        "DOCUMENT_CREATED"
        if getattr(instance, "_was_adding", created)
        else "DOCUMENT_UPDATED"
    )

    AuditLog.objects.create(
        actor=actor,
        action=action,
        model_name="Document",
        object_id=instance.id,
        metadata={
            "title": instance.title,
            "status": instance.status,
        },
    )
