from django.db import DatabaseError
from django.db.models import F

from .models import PageVisit


class PageVisitTrackingMiddleware:
    EXCLUDED_PREFIXES = ("/admin/", "/static/", "/favicon", "/robots.txt", "/sitemap.xml")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.method != "GET"
            or response.status_code >= 400
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or any(request.path.startswith(prefix) for prefix in self.EXCLUDED_PREFIXES)
            or "text/html" not in response.get("Content-Type", "")
        ):
            return response

        try:
            updated = PageVisit.objects.filter(path=request.path).update(total_views=F("total_views") + 1)
            if not updated:
                PageVisit.objects.create(
                    path=request.path,
                    title=getattr(response, "seo_title", "") or "",
                    total_views=1,
                )
            elif getattr(response, "seo_title", ""):
                PageVisit.objects.filter(path=request.path).update(title=response.seo_title)
        except DatabaseError:
            pass

        return response
