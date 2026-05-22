from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_update_category_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='mysql_id',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='entry',
            name='mysql_id',
            field=models.IntegerField(default=0),
        ),
    ]
