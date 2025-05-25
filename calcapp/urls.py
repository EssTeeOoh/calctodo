
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('calc/', views.calc, name='calc'),
    path('todolist/', views.todolist, name='todolist'),
    path('delete_task/<int:task_id>/', views.delete_task, name='delete_task'),
]
