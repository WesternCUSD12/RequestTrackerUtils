"""
Root-level views for rtutils project.
"""
from django.shortcuts import render


def home(request):
    """
    Homepage view displaying project overview and navigation.
    
    This view is protected by HTTP Basic Authentication via middleware.
    """
    return render(request, 'home.html')
