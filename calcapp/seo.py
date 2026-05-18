from django.urls import reverse


SEO_PAGES = [
    {
        "name": "home",
        "changefreq": "daily",
        "priority": "1.0",
        "title": "MultiApp Home",
        "description": "A compact collection of useful web tools including weather, calculator, trivia, news, and more.",
    },
    {
        "name": "calc",
        "changefreq": "weekly",
        "priority": "0.8",
        "title": "Free Online Calculator",
        "description": "Use a simple online calculator for addition, subtraction, multiplication, and division.",
    },
    {
        "name": "todolist",
        "changefreq": "weekly",
        "priority": "0.8",
        "title": "Simple To-Do List App",
        "description": "Organize your day with a clean and lightweight to-do list app.",
    },
    {
        "name": "currency",
        "changefreq": "daily",
        "priority": "0.8",
        "title": "Currency Converter",
        "description": "Convert currencies quickly with a simple browser-based exchange calculator.",
    },
    {
        "name": "news",
        "changefreq": "hourly",
        "priority": "0.8",
        "title": "Top News Headlines",
        "description": "Browse top headlines by category and region in a fast, clean news view.",
    },
    {
        "name": "trivia",
        "changefreq": "daily",
        "priority": "0.7",
        "title": "Trivia Quiz Game",
        "description": "Play a quick online trivia quiz with fresh multiple-choice questions.",
    },
    {
        "name": "tictactoe",
        "changefreq": "monthly",
        "priority": "0.6",
        "title": "Play Tic-Tac-Toe Online",
        "description": "Play a browser-based tic-tac-toe game against the computer.",
    },
]


def get_absolute_page_url(request, route_name):
    return request.build_absolute_uri(reverse(route_name))
