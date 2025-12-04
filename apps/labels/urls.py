from django.urls import path
from . import views

app_name = 'labels'

urlpatterns = [
    path('', views.label_home, name='home'),
    path('print', views.print_label, name='print'),
    path('batch', views.batch_labels, name='batch'),
    path('assets', views.search_assets_json, name='assets'),
    path('search-assets', views.search_assets_route, name='search'),
    path('direct-lookup', views.direct_lookup_route, name='direct_lookup'),
    path('fetch-assets', views.fetch_assets_direct, name='fetch'),
    path('get-asset-info', views.get_asset_info, name='info'),
    path('list-assets', views.list_assets, name='list'),
    path('debug-asset', views.debug_asset, name='debug'),
    path('test-api-methods', views.test_api_methods, name='test_api'),
]
