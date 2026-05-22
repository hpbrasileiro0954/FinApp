from decimal import Decimal

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Category, Entry


def _serialize(instance):
    """Return a JSON-safe dict of all model fields."""
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.attname)
        if isinstance(value, Decimal):
            value = str(value)
        elif hasattr(value, 'isoformat'):
            value = value.isoformat()
        data[field.attname] = value
    return data


def _create_log(instance, action, old_data, new_data):
    from .middleware import get_current_user
    from .models import AuditLog

    AuditLog.objects.create(
        table_name=instance._meta.db_table,
        record_id=instance.pk,
        action=action,
        changed_by=get_current_user(),
        old_data=old_data,
        new_data=new_data,
    )


@receiver(pre_save, sender=Category)
@receiver(pre_save, sender=Entry)
def capture_old_data(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._audit_old = _serialize(sender.objects.get(pk=instance.pk))
        except sender.DoesNotExist:
            instance._audit_old = None
    else:
        instance._audit_old = None


@receiver(post_save, sender=Category)
@receiver(post_save, sender=Entry)
def log_save(sender, instance, created, **kwargs):
    from .models import AuditLog

    old_data = getattr(instance, '_audit_old', None)
    new_data = _serialize(instance)

    if created:
        action = AuditLog.ACTION_INSERT
        old_data = None
    elif old_data and not old_data.get('is_deleted') and new_data.get('is_deleted'):
        action = AuditLog.ACTION_DELETE
    else:
        if old_data == new_data:
            return
        action = AuditLog.ACTION_UPDATE

    # Records with mysql_id=0 are local-only — no sync needed, so keep audit minimal.
    if getattr(instance, 'mysql_id', None) == 0:
        if action == AuditLog.ACTION_UPDATE:
            # Patch new_data on the original INSERT entry instead of adding a new row.
            AuditLog.objects.filter(
                table_name=instance._meta.db_table,
                record_id=instance.pk,
                action=AuditLog.ACTION_INSERT,
            ).update(new_data=new_data)
            return
        if action == AuditLog.ACTION_DELETE:
            # Remove the INSERT entry entirely — no trace needed for local-only records.
            AuditLog.objects.filter(
                table_name=instance._meta.db_table,
                record_id=instance.pk,
                action=AuditLog.ACTION_INSERT,
            ).delete()
            return

    _create_log(instance, action, old_data, new_data)


@receiver(post_delete, sender=Category)
@receiver(post_delete, sender=Entry)
def log_hard_delete(sender, instance, **kwargs):
    from .models import AuditLog

    if getattr(instance, 'mysql_id', None) == 0:
        AuditLog.objects.filter(
            table_name=instance._meta.db_table,
            record_id=instance.pk,
            action=AuditLog.ACTION_INSERT,
        ).delete()
        return

    _create_log(instance, AuditLog.ACTION_DELETE, _serialize(instance), None)
