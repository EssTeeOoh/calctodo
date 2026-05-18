import base64
import html
import logging
import os
import random
from datetime import date, datetime
from typing import Optional

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .forms import CalcForm, CurrencyForm, TaskForm
from .models import Task
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = (1.5, 2.5)
WEATHER_CACHE_TIMEOUT = 600
WEATHER_FALLBACK_CACHE_TIMEOUT = 180
HOLIDAY_CACHE_TIMEOUT = 60 * 60 * 12
TRIVIA_CACHE_TIMEOUT = 300
CURRENCY_API_ERROR_MESSAGE = "Exchange rates are temporarily unavailable. Please try again shortly."
MANUAL_WEATHER_LOCATIONS = {
    "lagos": {"label": "Lagos", "city": "Lagos", "lat": 6.4550, "lon": 3.3841},
    "abuja": {"label": "Abuja", "city": "Abuja", "lat": 9.0765, "lon": 7.3986},
    "portharcourt": {"label": "Port Harcourt", "city": "Port Harcourt", "lat": 4.8156, "lon": 7.0498},
    "london": {"label": "London", "city": "London", "lat": 51.5072, "lon": -0.1276},
    "newyork": {"label": "New York", "city": "New York", "lat": 40.7128, "lon": -74.0060},
    "toronto": {"label": "Toronto", "city": "Toronto", "lat": 43.6532, "lon": -79.3832},
}

quotes = [
    {"text": "No matter how long the rain lasts, the sun will shine again.", "author": "Nigerian Proverb"},
    {"text": "Life is like palm oil, it spreads everywhere.", "author": "Nigerian Saying"},
    {"text": "My bank account is like a horror movie.", "author": "Nigerian Twitter"},
    {"text": "If you're not fighting traffic in Lagos, are you even living?", "author": "Nigerian Twitter"},
    {"text": "When life gives you lemons, trade them for garri.", "author": "Nigerian Saying"},
    {"text": "A goat that climbs a tree has been drinking beer.", "author": "Nigerian Proverb"},
    {"text": "Your hustle will pay, even if it's selling pure water in traffic.", "author": "Nigerian Motivation"},
    {"text": "If NEPA takes light, your hustle shouldn't go dark.", "author": "Nigerian Twitter"},
    {"text": "The only thing faster than Usain Bolt is suya disappearing at a party.", "author": "Nigerian Twitter"},
    {"text": "No matter how hot the soup, it will always cool down.", "author": "Nigerian Proverb"},
    {"text": "If you dey wait for perfect time, you go wait tire.", "author": "Nigerian Pidgin Saying"},
    {"text": "Money no dey shout, but e dey whisper 'hustle harder.'", "author": "Nigerian Motivation"},
    {"text": "Person wey dey chop alone, dey die alone.", "author": "Nigerian Proverb"},
    {"text": "If your generator no dey shout, you no be true Nigerian.", "author": "Nigerian Twitter"},
    {"text": "Keep pushing, even if na wheelbarrow you dey push.", "author": "Nigerian Motivation"},
]


def fetch_location_data(ipinfo_api_token, user_ip):
    try:
        ipinfo_url = f"https://ipinfo.io/{user_ip}?token={ipinfo_api_token}"
        response = requests.get(ipinfo_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        city = data.get("city", "Unknown")
        loc = data.get("loc")
        if not loc:
            logger.error("No location data for IP %s", user_ip)
            return None

        lat, lon = loc.split(",")
        return {"city": city, "lat": float(lat), "lon": float(lon)}
    except Exception as exc:
        logger.error("Error fetching location data for IP %s: %s", user_ip, exc)
        return None


def fetch_weather_data(openweathermap_api_key, lat, lon):
    try:
        weather_url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={openweathermap_api_key}&units=metric"
        )
        response = requests.get(weather_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("Error fetching weather data for lat=%s, lon=%s: %s", lat, lon, exc)
        return {
            "name": "Unknown",
            "main": {"temp": "N/A"},
            "weather": [{"description": "Unable to fetch weather data", "icon": "unknown"}],
        }


def default_weather_data(city="Lagos"):
    return {
        "name": city,
        "main": {"temp": "N/A"},
        "weather": [{"description": "Weather update unavailable right now", "icon": "unknown"}],
    }


def detect_user_ip(request) -> Optional[str]:
    user_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    if user_ip in ("127.0.0.1", "localhost"):
        try:
            ip_response = requests.get("https://api.ipify.org?format=json", timeout=REQUEST_TIMEOUT)
            ip_response.raise_for_status()
            return ip_response.json().get("ip", "127.0.0.1")
        except Exception as exc:
            logger.warning("Falling back to local IP because public IP lookup failed: %s", exc)
            return user_ip
    return user_ip


def fetch_todays_holidays(today):
    holiday_cache_key = f"home_holidays_{today.isoformat()}"
    cached_holidays = cache.get(holiday_cache_key)
    if cached_holidays is not None:
        return cached_holidays

    holidays = []
    countries = [
        ("NG", "Nigeria"),
        ("US", "United States"),
        ("GB", "United Kingdom"),
        ("CA", "Canada"),
    ]

    for country_code, country_name in countries:
        try:
            response = requests.get(
                f"https://date.nager.at/api/v3/publicholidays/{today.year}/{country_code}",
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            for holiday in response.json():
                if holiday["date"] == str(today):
                    holidays.append(
                        {
                            "name": holiday["localName"],
                            "country": country_name,
                            "is_ng": country_code == "NG",
                        }
                    )
        except requests.RequestException as exc:
            logger.warning("Holiday lookup failed for %s: %s", country_code, exc)

    holidays.sort(key=lambda item: (not item["is_ng"], item["country"]))
    cache.set(holiday_cache_key, holidays, timeout=HOLIDAY_CACHE_TIMEOUT)
    return holidays


def fetch_weather_for_location(location):
    weather_data = fetch_weather_data(
        settings.OPENWEATHERMAP_API_KEY,
        location["lat"],
        location["lon"],
    )
    if weather_data.get("main", {}).get("temp") == "N/A":
        weather_data["name"] = location["city"]
    return weather_data


def render_page(request, template_name, context, seo_title):
    response = render(request, template_name, context)
    setattr(response, "seo_title", seo_title)
    return response


def robots_txt(request):
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {sitemap_url}",
        ]
    )
    return HttpResponse(content, content_type="text/plain")


def home(request):
    random_quote = random.choice(quotes)
    selected_location_key = request.GET.get("city", "").strip().lower()
    selected_manual_location = MANUAL_WEATHER_LOCATIONS.get(selected_location_key)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        response = JsonResponse(random_quote)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response

    cache_key = (
        f"weather_data_manual_{selected_location_key}"
        if selected_manual_location
        else f"weather_data_{request.META.get('REMOTE_ADDR', 'unknown')}"
    )
    weather_data = cache.get(cache_key)

    if not weather_data:
        try:
            if selected_manual_location:
                weather_data = fetch_weather_for_location(selected_manual_location)
                cache.set(
                    cache_key,
                    weather_data,
                    timeout=WEATHER_CACHE_TIMEOUT
                    if weather_data.get("main", {}).get("temp") != "N/A"
                    else WEATHER_FALLBACK_CACHE_TIMEOUT,
                )
            else:
                user_ip = detect_user_ip(request)
                location_data = fetch_location_data(settings.IPINFO_API_TOKEN, user_ip)
                if not location_data:
                    weather_data = default_weather_data()
                    cache.set(cache_key, weather_data, timeout=WEATHER_FALLBACK_CACHE_TIMEOUT)
                else:
                    weather_data = fetch_weather_for_location(location_data)
                    if weather_data.get("main", {}).get("temp") == "N/A":
                        cache.set(cache_key, weather_data, timeout=WEATHER_FALLBACK_CACHE_TIMEOUT)
                    else:
                        cache.set(cache_key, weather_data, timeout=WEATHER_CACHE_TIMEOUT)
        except Exception as exc:
            logger.warning("Error in weather fetch: %s", exc)
            fallback_city = selected_manual_location["city"] if selected_manual_location else "Lagos"
            weather_data = default_weather_data(fallback_city)
            cache.set(cache_key, weather_data, timeout=WEATHER_FALLBACK_CACHE_TIMEOUT)

    today = date.today()
    holidays = fetch_todays_holidays(today)

    return render_page(
        request,
        "calcapp/home.html",
        {
            "quote": random_quote,
            "weather": weather_data,
            "holidays": holidays,
            "today": today,
            "weather_locations": [(key, item["label"]) for key, item in MANUAL_WEATHER_LOCATIONS.items()],
            "selected_weather_location": selected_location_key,
            "using_manual_weather_location": bool(selected_manual_location),
        },
        seo_title="MultiApp Home",
    )


def calc(request):
    form = CalcForm(request.POST or None)
    result = None

    if request.method == "POST" and form.is_valid():
        num1 = form.cleaned_data["num1"]
        num2 = form.cleaned_data["num2"]
        operation = form.cleaned_data["operation"]

        if operation == "add":
            result = num1 + num2
        elif operation == "subtract":
            result = num1 - num2
        elif operation == "multiply":
            result = num1 * num2
        elif operation == "divide":
            result = num1 / num2 if num2 != 0 else "Error: Division by zero"

    return render_page(
        request,
        "calcapp/calc.html",
        {"form": form, "result": result},
        seo_title="Free Online Calculator",
    )


def todolist(request):
    tasks = Task.objects.all().order_by("-id")
    form = TaskForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("todolist")

    return render_page(
        request,
        "calcapp/todolist.html",
        {"tasks": tasks, "form": form},
        seo_title="Simple To-Do List App",
    )


def delete_task(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, id=task_id)
        task.delete()
    return redirect("todolist")


def currency(request):
    form = CurrencyForm(request.POST or None)
    result = None
    from_currency = None
    to_currency = None
    amount = None

    if request.method == "POST" and form.is_valid():
        amount = form.cleaned_data["amount"]
        from_currency = form.cleaned_data["from_currency"]
        to_currency = form.cleaned_data["to_currency"]

        try:
            response = requests.get(
                f"https://api.exchangerate-api.com/v4/latest/{from_currency}",
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            rate = data["rates"].get(to_currency)
            if rate:
                result = round(amount * rate, 2)
            else:
                form.add_error(None, "Invalid currency pair.")
        except requests.RequestException as exc:
            logger.warning("Currency conversion lookup failed for %s to %s: %s", from_currency, to_currency, exc)
            form.add_error(None, CURRENCY_API_ERROR_MESSAGE)

    return render_page(
        request,
        "calcapp/currency.html",
        {
            "form": form,
            "result": result,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
        },
        seo_title="Currency Converter",
    )


def news(request):
    api_key = os.getenv("NEWSAPI_KEY")
    category = request.GET.get("category", "general")
    country = request.GET.get("country", "")
    articles = []
    error = None

    def fetch_news(country_param, category_param):
        url = f"https://newsapi.org/v2/top-headlines?category={category_param}&apiKey={api_key}"
        if country_param:
            url += f"&country={country_param}"

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            stories = []

            for article in data.get("articles", [])[:6]:
                published_display = None
                published_at = article.get("publishedAt")
                if published_at:
                    try:
                        parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        published_display = parsed.strftime("%b %d, %Y %H:%M")
                    except ValueError:
                        published_display = published_at

                stories.append(
                    {
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "url": article.get("url"),
                        "source_name": article.get("source", {}).get("name"),
                        "published_display": published_display,
                    }
                )

            return stories, None
        except requests.RequestException as exc:
            logger.error("News fetch failed for category=%s country=%s: %s", category_param, country_param, exc)
            return [], str(exc)

    if api_key:
        articles, error = fetch_news(country, category)
        if not articles and country:
            articles, error = fetch_news("", category)
    else:
        error = "News API key is missing."

    countries = [
        ("", "Global"),
        ("ng", "Nigeria"),
        ("us", "United States"),
        ("gb", "United Kingdom"),
    ]
    categories = [
        ("general", "General"),
        ("business", "Business"),
        ("technology", "Technology"),
        ("sports", "Sports"),
        ("entertainment", "Entertainment"),
    ]

    return render_page(
        request,
        "calcapp/news.html",
        {
            "articles": articles,
            "error": error,
            "current_category": category,
            "current_country": country,
            "current_country_label": dict(countries).get(country, "Global"),
            "categories": categories,
            "countries": countries,
        },
        seo_title="Top News Headlines",
    )


def tictactoe(request):
    return render_page(request, "calcapp/tictactoe.html", {}, seo_title="Play Tic-Tac-Toe Online")


def trivia(request):
    cache_key = "trivia_questions"
    questions = []
    error = None
    score = None
    user_answers = None

    if request.method == "POST":
        user_answers = {key: value for key, value in request.POST.items() if key.startswith("answer_")}
        questions = cache.get(cache_key)
        if questions:
            score = 0
            for index, question in enumerate(questions):
                if user_answers.get(f"answer_{index}") == question["correct_answer"]:
                    score += 1
        else:
            error = "Questions expired. Please start a new quiz."

    if request.method == "GET":
        cache.delete(cache_key)

        try:

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=6),
                retry=retry_if_exception_type(requests.exceptions.RequestException),
            )
            def fetch_trivia_questions():
                response = requests.get(
                    "https://opentdb.com/api.php",
                    params={"amount": 5, "type": "multiple", "encode": "base64"},
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()

            data = fetch_trivia_questions()
            if data["response_code"] == 0:
                questions = []
                for item in data["results"]:
                    question_text = html.unescape(base64.b64decode(item["question"]).decode("utf-8"))
                    correct_answer = html.unescape(base64.b64decode(item["correct_answer"]).decode("utf-8"))
                    incorrect_answers = [
                        html.unescape(base64.b64decode(answer).decode("utf-8"))
                        for answer in item["incorrect_answers"]
                    ]
                    all_answers = incorrect_answers + [correct_answer]
                    random.shuffle(all_answers)
                    questions.append(
                        {
                            "question": question_text,
                            "correct_answer": correct_answer,
                            "answers": all_answers,
                        }
                    )
                cache.set(cache_key, questions, timeout=TRIVIA_CACHE_TIMEOUT)
            else:
                error = "Unable to fetch trivia questions. Please try again later."
                logger.error("Open Trivia DB API response code: %s", data["response_code"])
        except (requests.RequestException, RetryError, ValueError, KeyError) as exc:
            error = "Unable to fetch trivia questions. Please try again later."
            logger.error("Error fetching trivia data: %s", exc)

    total = len(questions) if questions else len(cache.get(cache_key) or [])
    return render_page(
        request,
        "calcapp/trivia.html",
        {
            "questions": questions,
            "error": error,
            "score": score,
            "total": total,
            "user_answers": user_answers,
        },
        seo_title="Trivia Quiz Game",
    )
