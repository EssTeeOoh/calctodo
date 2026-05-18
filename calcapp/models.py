from django.db import models


class Task(models.Model):
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description


class PageVisit(models.Model):
    path = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True)
    total_views = models.PositiveIntegerField(default=0)
    last_visited = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_views", "path"]

    def __str__(self):
        return f"{self.path} ({self.total_views})"
