from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
import requests
from .forms import CalcForm, TaskForm, CurrencyForm  
import random
from django.core.cache import cache
from .models import Task
import os
import logging
from datetime import date, datetime
from django.core.cache import cache



logger = logging.getLogger(__name__)

EVENTBRITE_CATEGORIES = {
    'music': '103',
    'business': '101',
    'food_drink': '110',
    'arts': '105',
}

# List of Nigerian funny and motivational quotes 
quotes = [
    {"text": "No matter how long the rain lasts, the sun will shine again.", "author": "Nigerian Proverb"},
    {"text": "Life is like palm oil, it spreads everywhere.", "author": "Nigerian Saying"},
    {"text": "My bank account is like a horror movie.", "author": "Nigerian Twitter"},
    {"text": "If you’re not fighting traffic in Lagos, are you even living?", "author": "Nigerian Twitter"},
    {"text": "When life gives you lemons, trade them for garri.", "author": "Nigerian Saying"},
    {"text": "A goat that climbs a tree has been drinking beer.", "author": "Nigerian Proverb"},
    {"text": "Your hustle will pay, even if it’s selling pure water in traffic.", "author": "Nigerian Motivation"},
    {"text": "If NEPA takes light, your hustle shouldn’t go dark.", "author": "Nigerian Twitter"},
    {"text": "The only thing faster than Usain Bolt is suya disappearing at a party.", "author": "Nigerian Twitter"},
    {"text": "No matter how hot the soup, it will always cool down.", "author": "Nigerian Proverb"},
    {"text": "If you dey wait for perfect time, you go wait tire.", "author": "Nigerian Pidgin Saying"},
    {"text": "Money no dey shout, but e dey whisper ‘hustle harder.’", "author": "Nigerian Motivation"},
    {"text": "Person wey dey chop alone, dey die alone.", "author": "Nigerian Proverb"},
    {"text": "If your generator no dey shout, you no be true Nigerian.", "author": "Nigerian Twitter"},
    {"text": "Keep pushing, even if na wheelbarrow you dey push.", "author": "Nigerian Motivation"},
]

def fetch_location_data(ipinfo_api_token, user_ip):
    try:
        ipinfo_url = f"https://ipinfo.io/{user_ip}?token={ipinfo_api_token}"
        response = requests.get(ipinfo_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        city = data.get('city', 'Unknown')
        loc = data.get('loc')
        if loc:
            lat, lon = loc.split(',')
            return {'city': city, 'lat': float(lat), 'lon': float(lon)}
        else:
            logger.error(f"No location data for IP {user_ip}")
            return None
    except Exception as e:
        logger.error(f"Error fetching location data for IP {user_ip}: {e}")
        return None

def fetch_weather_data(openweathermap_api_key, lat, lon):
    try:
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={openweathermap_api_key}&units=metric"
        response = requests.get(weather_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching weather data for lat={lat}, lon={lon}: {e}")
        return {
            'name': 'Unknown',
            'main': {'temp': 'N/A'},
            'weather': [{'description': 'Unable to fetch weather data', 'icon': 'unknown'}],
        }

def home(request):
    openweathermap_api_key = os.getenv('OPENWEATHERMAP_API_KEY')
    ipinfo_api_token = os.getenv('IPINFO_TOKEN')

    # Select a random quote
    random_quote = random.choice(quotes)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = JsonResponse(random_quote)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    # Fetch or use cached weather data
    cache_key = f"weather_data_{request.META.get('REMOTE_ADDR', 'unknown')}"
    weather_data = cache.get(cache_key)
    if not weather_data:
        try:
            user_ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
            )
            logger.debug(f"Detected IP: {user_ip}")

            if user_ip in ('127.0.0.1', 'localhost'):
                try:
                    ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
                    ip_response.raise_for_status()
                    user_ip = ip_response.json().get('ip', '127.0.0.1')
                    logger.debug(f"Fetched public IP: {user_ip}")
                except Exception as e:
                    logger.error(f"Error fetching public IP: {e}")

            location_data = fetch_location_data(ipinfo_api_token, user_ip)

            if not location_data:
                location_data = {
                    'city': 'Lagos',
                    'lat': 6.4388,
                    'lon': 3.5198,
                }

            city = location_data['city']
            lat = location_data['lat']
            lon = location_data['lon']

            weather_data = fetch_weather_data(openweathermap_api_key, lat, lon)

            if not weather_data:
                weather_data = {
                    'name': 'Lagos',
                    'main': {'temp': 'N/A'},
                    'weather': [{'description': 'Unable to fetch weather data', 'icon': 'unknown'}],
                }

            cache.set(cache_key, weather_data, timeout=600)
        except Exception as e:
            logger.error(f"Error in weather fetch: {e}")
            weather_data = {
                'name': 'Lagos',
                'main': {'temp': 'N/A'},
                'weather': [{'description': 'Unable to fetch weather data', 'icon': 'unknown'}],
            }

    # Fetch today's holidays
    today = date.today()
    year = today.year
    holidays = []
    countries = [
        ('NG', 'Nigeria'),
        ('US', 'United States'),
        ('GB', 'United Kingdom'),
        ('CA', 'Canada'),
    ]

    for country_code, country_name in countries:
        try:
            print(f"Requesting Holidays: https://date.nager.at/api/v3/publicholidays/{year}/{country_code}")
            response = requests.get(
                f"https://date.nager.at/api/v3/publicholidays/{year}/{country_code}",
                timeout=5
            )
            response.raise_for_status()
            country_holidays = response.json()
            for holiday in country_holidays:
                if holiday['date'] == str(today):
                    holidays.append({
                        'name': holiday['localName'],
                        'country': country_name,
                        'is_ng': country_code == 'NG',
                    })
        except requests.RequestException as e:
            logger.error(f"Error fetching holidays for {country_code}: {e}")

    # Sort holidays: Nigeria first
    holidays.sort(key=lambda x: (not x['is_ng'], x['country']))

    context = {
        'quote': random_quote,
        'weather': weather_data,
        'holidays': holidays,
        'today': today,
    }
    return render(request, 'calcapp/home.html', context)

def calc(request):
    form = CalcForm(request.POST or None)
    result = None
    if request.method == 'POST' and form.is_valid():
        num1 = form.cleaned_data['num1']
        num2 = form.cleaned_data['num2']
        operation = form.cleaned_data['operation']
        if operation == 'add':
            result = num1 + num2
        elif operation == 'subtract':
            result = num1 - num2
        elif operation == 'multiply':
            result = num1 * num2
        elif operation == 'divide':
            result = num1 / num2 if num2 != 0 else 'Error: Division by zero'
    return render(request, 'calcapp/calc.html', {'form': form, 'result': result})

def todolist(request):
    tasks = Task.objects.all()
    form = TaskForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('todolist')
    return render(request, 'calcapp/todolist.html', {'tasks': tasks, 'form': form})

def delete_task(request, task_id):
    if request.method == 'POST':
        task = Task.objects.get(id=task_id)
        task.delete()
    return redirect('todolist')


def currency(request):
    form = CurrencyForm(request.POST or None)
    result = None
    from_currency = None
    to_currency = None
    amount = None
    api_key = os.getenv('EXCHANGERATE_API_KEY')

    if request.method == 'POST' and form.is_valid():
        amount = form.cleaned_data['amount']
        from_currency = form.cleaned_data['from_currency']
        to_currency = form.cleaned_data['to_currency']
        try:
            response = requests.get(
                f'https://api.exchangerate-api.com/v4/latest/{from_currency}',
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            rate = data['rates'].get(to_currency)
            if rate:
                result = round(amount * rate, 2)
            else:
                form.add_error(None, 'Invalid currency pair.')
        except requests.RequestException as e:
            form.add_error(None, f'API error: {str(e)}')

    return render(request, 'calcapp/currency.html', {
        'form': form,
        'result': result,
        'from_currency': from_currency,
        'to_currency': to_currency,
        'amount': amount
    })


def news(request):
    api_key = os.getenv('NEWSAPI_KEY')
    category = request.GET.get('category', 'general')
    country = request.GET.get('country', '')  # Default to no country
    articles = []
    error = None
    def fetch_news(country_param, category_param):
        url = f'https://newsapi.org/v2/top-headlines?category={category_param}&apiKey={api_key}'
        if country_param:
            url += f'&country={country_param}'
        print(f"Requesting NewsAPI: {url}")
        try:
            response = requests.get(url, url, timeout=5)
            response.raise_for_status()
            data = response.json()
            print(f"Response: {data}")
            return data.get('articles', [])[:5], None  # Limit to 5
        except requests.RequestException as e:
            print(f"Error: {str(e)}")
            return [], str(e)

    # Try with selected country (if any)
    if api_key:
        articles, error = fetch_news(country, category)
        # Fallback to global if no articles or error
        if not articles and country:
            print("Falling back to global news")
            articles, error = fetch_news('', category)
    else:
        error = "News API key is missing."

    countries = [
        ('', 'Global'),
        ('ng', 'Nigeria'),
        ('us', 'United States'),
        ('gb', 'United Kingdom'),
    ]
    categories = [
        ('general', 'General'),
        ('business', 'Business'),
        ('technology', 'Technology'),
        ('sports', 'Sports'),
        ('entertainment', 'Entertainment'),
    ]

    return render(request, 'calcapp/news.html', {
        'articles': articles,
        'error': error,
        'current_category': category,
        'current_country': country,
        'categories': categories,
        'countries': countries,
    })

def tictactoe(request):
    return render(request, 'calcapp/tictactoe.html')

def crypto(request):
    cache_key = 'crypto_data'
    coins = cache.get(cache_key)
    error = None

    if not coins:
        try:
            response = requests.get(
                'https://api.coingecko.com/api/v3/coins/markets',
                params={
                    'vs_currency': 'usd',
                    'ids': 'bitcoin,ethereum,tether,binancecoin,solana',
                    'order': 'market_cap_desc',
                    'per_page': 5,
                    'page': 1,
                    'sparkline': 'false',
                    'price_change_percentage': '24h'
                },
                timeout=5
            )
            response.raise_for_status()
            coins = response.json()
            cache.set(cache_key, coins, timeout=180)  # Cache for 5 minutes
        except requests.RequestException as e:
            logger.error(f"Error fetching crypto data: {e}")
            coins = []
            error = "Unable to fetch crypto data. Please try again later."

    return render(request, 'calcapp/crypto.html', {
        'coins': coins,
        'error': error if not coins else None
    })