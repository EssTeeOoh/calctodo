from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .seo import SEO_PAGES


class CalcAppSitemap(Sitemap):
    protocol = "https"

    def items(self):
        return SEO_PAGES

    def location(self, item):
        return reverse(item["name"])

    def changefreq(self, item):
        return item["changefreq"]

    def priority(self, item):
        return item["priority"]
