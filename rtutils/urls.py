"""
URL configuration for rtutils project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views as root_views
from apps.assets import views as assets_views

from django.views.generic.base import RedirectView

urlpatterns = [
    # Favicon
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.svg')),

    # Django admin (protected by admin auth)
    path('admin/', admin.site.urls),
    
    # OAuth2 Authentication (Feature 006-google-auth)
    path('auth/', include('apps.authentication.urls')),
    
    # Labels app (PUBLIC - no auth via middleware)
    path('labels/', include('apps.labels.urls')),
    
    # Devices app (PROTECTED)
    path('devices/', include('apps.devices.urls')),
    
    # Audit app (PROTECTED, nested under /devices)
    path('devices/audit/', include('apps.audit.urls')),
    
    # Students app (PROTECTED)
    path('students/', include('apps.students.urls')),
    
    # Assets app (PROTECTED)
    path('assets/', include('apps.assets.urls')),
    
    # Root-level routes (PROTECTED)
    path('', root_views.home, name='home'),
    path('next-asset-tag', assets_views.next_tag, name='next_tag'),
    path('confirm-asset-tag', assets_views.confirm_tag, name='confirm_tag'),
    path('reset-asset-tag', assets_views.reset_tag, name='reset_tag'),
    path('update-asset-name', assets_views.update_name, name='update_name'),
    path('webhook/asset-created', assets_views.webhook_created, name='webhook'),
]

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# ... (existing code)

if settings.DEBUG:
    # Add static files serving for development
    urlpatterns += staticfiles_urlpatterns()
    # Add media files serving for development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
