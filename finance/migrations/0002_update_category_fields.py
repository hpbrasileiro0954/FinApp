from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='category', name='label'),
        migrations.RemoveField(model_name='category', name='value'),
        migrations.RemoveField(model_name='category', name='default'),
        migrations.AddField(
            model_name='category',
            name='name',
            field=models.CharField(blank=True, max_length=512, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='category',
            name='published',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='category',
            name='vl_prev',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='category',
            name='day_prev',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='category',
            name='ordem',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='category',
            name='type',
            field=models.CharField(blank=True, max_length=25, default=''),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='category',
            options={'db_table': 'categories', 'ordering': ['name']},
        ),
    ]
