from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calcapp", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PageVisit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("path", models.CharField(max_length=255, unique=True)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("total_views", models.PositiveIntegerField(default=0)),
                ("last_visited", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-total_views", "path"],
            },
        ),
    ]
