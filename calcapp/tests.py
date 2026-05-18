from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from tenacity import RetryError

from .models import PageVisit, Task


class ToDoTests(TestCase):
    def test_can_create_task(self):
        response = self.client.post(reverse("todolist"), {"description": "Buy milk"})

        self.assertRedirects(response, reverse("todolist"))
        self.assertTrue(Task.objects.filter(description="Buy milk").exists())

    def test_delete_missing_task_returns_404(self):
        response = self.client.post(reverse("delete_task", args=[999]))

        self.assertEqual(response.status_code, 404)

    def test_page_visit_tracking_records_html_page(self):
        self.client.get(reverse("calc"))

        visit = PageVisit.objects.get(path=reverse("calc"))
        self.assertEqual(visit.total_views, 1)
        self.assertEqual(visit.title, "Free Online Calculator")


class HomeTests(TestCase):
    @patch("calcapp.views.fetch_weather_data")
    @patch("calcapp.views.fetch_location_data")
    @patch("calcapp.views.requests.get")
    def test_home_uses_configured_ipinfo_token(self, mock_requests_get, mock_location, mock_weather):
        cache.clear()
        mock_location.return_value = {"city": "Lagos", "lat": 6.4, "lon": 3.5}
        mock_weather.return_value = {
            "name": "Lagos",
            "main": {"temp": 30},
            "weather": [{"description": "clear sky", "icon": "01d"}],
        }
        holiday_response = Mock()
        holiday_response.raise_for_status.return_value = None
        holiday_response.json.return_value = []
        mock_requests_get.return_value = holiday_response

        self.client.get(reverse("home"), REMOTE_ADDR="8.8.8.8")

        called_token = mock_location.call_args[0][0]
        self.assertTrue(called_token)

    @patch("calcapp.views.requests.get")
    @patch("calcapp.views.fetch_location_data")
    def test_home_caches_weather_fallback_when_location_lookup_fails(self, mock_location, mock_get):
        cache.clear()
        mock_location.return_value = None
        holiday_response = Mock()
        holiday_response.raise_for_status.return_value = None
        holiday_response.json.return_value = []
        mock_get.return_value = holiday_response

        response = self.client.get(reverse("home"), REMOTE_ADDR="8.8.8.8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["weather"]["main"]["temp"], "N/A")
        self.assertIsNotNone(cache.get("weather_data_8.8.8.8"))

    @patch("calcapp.views.fetch_weather_data")
    @patch("calcapp.views.fetch_location_data")
    @patch("calcapp.views.requests.get")
    def test_home_holidays_are_cached(self, mock_get, mock_location, mock_weather):
        cache.clear()
        mock_location.return_value = {"city": "Lagos", "lat": 6.4, "lon": 3.5}
        mock_weather.return_value = {
            "name": "Lagos",
            "main": {"temp": 30},
            "weather": [{"description": "clear sky", "icon": "01d"}],
        }
        holiday_response = Mock()
        holiday_response.raise_for_status.return_value = None
        holiday_response.json.return_value = []
        mock_get.return_value = holiday_response

        self.client.get(reverse("home"), REMOTE_ADDR="8.8.8.8")
        self.client.get(reverse("home"), REMOTE_ADDR="8.8.8.8")

        self.assertEqual(mock_get.call_count, 4)

    @patch("calcapp.views.fetch_weather_data")
    def test_home_allows_manual_weather_city_selection(self, mock_weather):
        cache.clear()
        mock_weather.return_value = {
            "name": "London",
            "main": {"temp": 18},
            "weather": [{"description": "light rain", "icon": "10d"}],
        }

        response = self.client.get(reverse("home"), {"city": "london"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["weather"]["name"], "London")
        self.assertTrue(response.context["using_manual_weather_location"])
        mock_weather.assert_called_once()


class CurrencyTests(TestCase):
    @patch("calcapp.views.requests.get")
    def test_currency_page_shows_api_errors(self, mock_get):
        mock_get.side_effect = requests.RequestException("boom")

        response = self.client.post(
            reverse("currency"),
            {"amount": 10, "from_currency": "USD", "to_currency": "NGN"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exchange rates are temporarily unavailable")


class NewsTests(TestCase):
    @patch("calcapp.views.requests.get")
    def test_news_renders_story_cards(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "articles": [
                {
                    "title": "Story title",
                    "description": "Story description",
                    "url": "https://example.com/story",
                    "source": {"name": "Example"},
                    "publishedAt": "2025-05-18T10:00:00Z",
                }
            ]
        }
        mock_get.return_value = mock_response

        response = self.client.get(reverse("news"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Story title")


class TriviaTests(TestCase):
    @patch("calcapp.views.requests.get")
    def test_trivia_handles_retried_api_failure_without_500(self, mock_get):
        mock_get.side_effect = requests.RequestException("network down")

        response = self.client.get(reverse("trivia"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unable to fetch trivia questions")


class SeoRoutesTests(TestCase):
    def test_robots_txt_exposes_sitemap(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sitemap:")

    def test_sitemap_xml_renders(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("home"))
