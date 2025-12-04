"""URL configuration for LDAP authentication."""

from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # LDAP authentication routes (Feature 006-ldap-auth)
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
]

