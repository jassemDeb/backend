# Generated by Django 4.2.10 on 2025-04-22 13:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat_api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="fullname",
            field=models.CharField(
                default="", max_length=255, verbose_name="Full Name"
            ),
            preserve_default=False,
        ),
    ]
