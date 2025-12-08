"""
Asset views for managing RT assets.

⚠️ NOTE: Asset creation/management features are OUT OF SCOPE for feature 007-unified-student-data.
These placeholder views are retained for reference only. Asset creation is handled via
the request_tracker_utils Flask app, not Django.

Future Feature: Asset management migration to Django would be a separate feature request.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def create_asset(request):
    """Asset creation - OUT OF SCOPE for 007"""
    return JsonResponse(
        {'error': 'Asset creation is not yet implemented in Django. Use the Flask app.'},
        status=501
    )


@require_http_methods(["GET"])
def next_tag(request):
    """Get next asset tag - OUT OF SCOPE for 007"""
    return JsonResponse(
        {'error': 'Asset tag management is not yet implemented in Django. Use the Flask app.'},
        status=501
    )


@require_http_methods(["POST"])
def confirm_tag(request):
    """Confirm asset tag - OUT OF SCOPE for 007"""
    return JsonResponse(
        {'error': 'Asset tag management is not yet implemented in Django. Use the Flask app.'},
        status=501
    )


@require_http_methods(["POST"])
def reset_tag(request):
    """Reset tag sequence - OUT OF SCOPE for 007"""
    return JsonResponse(
        {'error': 'Asset tag management is not yet implemented in Django. Use the Flask app.'},
        status=501
    )


@require_http_methods(["POST"])
def update_name(request):
    """Update asset name - OUT OF SCOPE for 007"""
    return JsonResponse(
        {'error': 'Asset management is not yet implemented in Django. Use the Flask app.'},
        status=501
    )


@require_http_methods(["POST"])
def webhook_created(request):
    """RT webhook handler - OUT OF SCOPE for 007"""
    return JsonResponse(
        {'error': 'RT webhooks are not yet implemented in Django. Use the Flask app.'},
        status=501
    )
