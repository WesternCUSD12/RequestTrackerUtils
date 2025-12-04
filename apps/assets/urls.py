"""
URL configuration for the assets app
"""
from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    # Asset creation route
    path('create', views.create_asset, name='create'),
]
