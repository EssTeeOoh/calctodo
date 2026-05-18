from django.contrib import admin

from .models import PageVisit, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "description")
    search_fields = ("description",)


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ("path", "title", "total_views", "last_visited")
    search_fields = ("path", "title")
    ordering = ("-total_views",)
