from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
import requests
import random
from django.core.cache import cache
from .models import Task
import os
import logging

logger = logging.getLogger(__name__)

# List of Nigerian funny and motivational quotes (deduplicated)
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
            # Get user's public IP
            user_ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
            )
            logger.debug(f"Detected IP: {user_ip}")

            # Use external service for local testing
            if user_ip in ('127.0.0.1', 'localhost'):
                try:
                    ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
                    ip_response.raise_for_status()
                    user_ip = ip_response.json().get('ip', '127.0.0.1')
                    logger.debug(f"Fetched public IP: {user_ip}")
                except Exception as e:
                    logger.error(f"Error fetching public IP: {e}")

            # Fetch location data
            location_data = fetch_location_data(ipinfo_api_token, user_ip)

            # Default to Lagos if location unavailable
            if not location_data:
                location_data = {
                    'city': 'Lagos',
                    'lat': 6.4388,
                    'lon': 3.5198,
                }

            city = location_data['city']
            lat = location_data['lat']
            lon = location_data['lon']

            # Fetch weather data
            weather_data = fetch_weather_data(openweathermap_api_key, lat, lon)

            # Cache for 10 minutes
            cache.set(cache_key, weather_data, timeout=600)
        except Exception as e:
            logger.error(f"Error in weather fetch: {e}")
            weather_data = {
                'name': 'Lagos',
                'main': {'temp': 'N/A'},
                'weather': [{'description': 'Unable to fetch weather data', 'icon': 'unknown'}],
            }

    context = {
        'quote': random_quote,
        'weather': weather_data,
    }
    return render(request, 'calcapp/home.html', context)

def calc(request):
    result = None
    if request.method == 'POST':
        num1 = float(request.POST.get('num1'))
        num2 = float(request.POST.get('num2'))
        operation = request.POST.get('operation')
        if operation == 'add':
            result = num1 + num2
        elif operation == 'subtract':
            result = num1 - num2
        elif operation == 'multiply':
            result = num1 * num2
        elif operation == 'divide':
            result = num1 / num2 if num2 != 0 else "Error: Division by zero"
    return render(request, 'calcapp/calc.html', {'result': result})

def todolist(request):
    if request.method == 'POST':
        task_description = request.POST.get('task')
        if task_description:
            Task.objects.create(description=task_description)
            return redirect('todolist')
    tasks = Task.objects.all()
    return render(request, 'calcapp/todolist.html', {'tasks': tasks})

def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return redirect('todolist')