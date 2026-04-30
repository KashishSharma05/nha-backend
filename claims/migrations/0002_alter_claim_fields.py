# Generated migration — adds source field and makes title/description/document optional

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Make title optional with empty string default
        migrations.AlterField(
            model_name='claim',
            name='title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        # Make description optional with empty string default
        migrations.AlterField(
            model_name='claim',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        # Make document optional (null allowed)
        migrations.AlterField(
            model_name='claim',
            name='document',
            field=models.FileField(blank=True, null=True, upload_to='claims/'),
        ),
        # Add new source field
        migrations.AddField(
            model_name='claim',
            name='source',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]
