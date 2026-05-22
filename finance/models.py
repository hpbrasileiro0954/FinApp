from django.conf import settings
from django.db import models


class Param(models.Model):
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100, blank=True)
    value = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'params'

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=512, blank=True)
    published = models.BooleanField(default=False)
    vl_prev = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    day_prev = models.IntegerField(default=0)
    ordem = models.IntegerField(default=0)
    type = models.CharField(max_length=25, blank=True)
    is_deleted = models.BooleanField(default=False)
    mysql_id = models.IntegerField(default=0)

    class Meta:
        db_table = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Entry(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='entries')
    ds_category = models.CharField(max_length=255)
    ds_subcategory = models.CharField(max_length=255, blank=True)
    details = models.TextField(blank=True)
    dt_entry = models.DateField()
    vl_entry = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.BooleanField(default=False)
    fixed = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    mysql_id = models.IntegerField(default=0)

    class Meta:
        db_table = 'entries'
        ordering = ['dt_entry']

    def __str__(self):
        return f'{self.dt_entry} - {self.ds_category}'


class Fact(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.PROTECT, related_name='facts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facts'

    def __str__(self):
        return f'Fact #{self.pk} - Entry #{self.entry_id}'


class AuditLog(models.Model):
    ACTION_INSERT = 'INSERT'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'

    ACTION_CHOICES = [
        (ACTION_INSERT, 'Insert'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
    ]

    table_name = models.CharField(max_length=50)
    record_id = models.BigIntegerField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    export_warning = models.BooleanField(default=False)
    export_warning_msg = models.CharField(max_length=512, blank=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.action} {self.table_name} #{self.record_id} at {self.changed_at}'
