import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_add_mysql_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('table_name', models.CharField(max_length=50)),
                ('record_id', models.BigIntegerField()),
                ('action', models.CharField(
                    choices=[('INSERT', 'Insert'), ('UPDATE', 'Update'), ('DELETE', 'Delete')],
                    max_length=10,
                )),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('old_data', models.JSONField(blank=True, null=True)),
                ('new_data', models.JSONField(blank=True, null=True)),
                ('changed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audit_logs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'audit_log',
                'ordering': ['-changed_at'],
            },
        ),
    ]
