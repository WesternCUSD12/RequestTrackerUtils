# URL Routing Contracts

**Feature**: 005-django-refactor  
**Date**: 2025-12-01

---

## Authentication Summary

| Route Prefix  | Auth Required | Reason                                                            |
| ------------- | ------------- | ----------------------------------------------------------------- |
| `/labels/*`   | ❌ No         | External systems (RT webhooks, label printers) need public access |
| `/devices/*`  | ✅ Yes        | Internal device management                                        |
| `/students/*` | ✅ Yes        | Internal student data                                             |
| `/assets/*`   | ✅ Yes        | Asset tag management                                              |
| `/admin/*`    | ✅ Yes        | Django admin interface                                            |
| `/`           | ✅ Yes        | Homepage                                                          |

---

## Labels App (PUBLIC)

**App**: `apps.labels`  
**URL Prefix**: `/labels`  
**Authentication**: None required

| Method    | URL Pattern                | View                  | Description                                           |
| --------- | -------------------------- | --------------------- | ----------------------------------------------------- |
| GET       | `/labels/`                 | `label_home`          | Label printing form                                   |
| GET       | `/labels/print`            | `print_label`         | Print single label (params: assetId, assetName, size) |
| GET, POST | `/labels/batch`            | `batch_labels`        | Batch label generation                                |
| POST      | `/labels/assets`           | `search_assets_json`  | Search assets with JSON query                         |
| GET       | `/labels/search-assets`    | `search_assets_route` | Search assets by name                                 |
| GET       | `/labels/direct-lookup`    | `direct_lookup_route` | Direct asset lookup                                   |
| GET       | `/labels/fetch-assets`     | `fetch_assets_direct` | Fetch assets list                                     |
| GET       | `/labels/get-asset-info`   | `get_asset_info`      | Get asset details                                     |
| GET       | `/labels/list-assets`      | `list_assets`         | List sample assets                                    |
| GET       | `/labels/debug-asset`      | `debug_asset`         | Debug asset lookup                                    |
| GET       | `/labels/test-api-methods` | `test_api_methods`    | Test RT API methods                                   |

**URLconf**: `apps/labels/urls.py`

```python
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
```

---

## Devices App (PROTECTED)

**App**: `apps.devices`  
**URL Prefix**: `/devices`  
**Authentication**: HTTP Basic Auth

| Method | URL Pattern                      | View               | Description             |
| ------ | -------------------------------- | ------------------ | ----------------------- |
| GET    | `/devices/check-in`              | `check_in_home`    | Device check-in form    |
| GET    | `/devices/check-in/<asset_name>` | `check_in_asset`   | Check-in specific asset |
| POST   | `/devices/check-in`              | `process_check_in` | Process device check-in |
| GET    | `/devices/check-out`             | `check_out_home`   | Device check-out form   |
| GET    | `/devices/logs`                  | `check_in_logs`    | View check-in logs      |

**URLconf**: `apps/devices/urls.py`

```python
from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    path('check-in', views.check_in_home, name='check_in'),
    path('check-in/<str:asset_name>', views.check_in_asset, name='check_in_asset'),
    path('check-out', views.check_out_home, name='check_out'),
    path('logs', views.check_in_logs, name='logs'),
]
```

---

## Audit App (PROTECTED)

**App**: `apps.audit`  
**URL Prefix**: `/devices/audit`  
**Authentication**: HTTP Basic Auth

| Method | URL Pattern                                     | View                 | Description                 |
| ------ | ----------------------------------------------- | -------------------- | --------------------------- |
| GET    | `/devices/audit`                                | `audit_home`         | Audit session home          |
| POST   | `/devices/audit/upload`                         | `upload_csv`         | Upload student CSV          |
| GET    | `/devices/audit/session/<session_id>`           | `view_session`       | View audit session          |
| GET    | `/devices/audit/session/<session_id>/students`  | `session_students`   | Get students (JSON)         |
| GET    | `/devices/audit/student/<student_id>`           | `student_detail`     | Student device verification |
| GET    | `/devices/audit/student/<student_id>/devices`   | `student_devices`    | Student's devices           |
| POST   | `/devices/audit/student/<student_id>/verify`    | `verify_student`     | Mark student audited        |
| POST   | `/devices/audit/student/<student_id>/re-audit`  | `re_audit_student`   | Reset audit status          |
| GET    | `/devices/audit/session/<session_id>/completed` | `completed_students` | View completed audits       |
| GET    | `/devices/audit/notes`                          | `audit_notes`        | View/filter audit notes     |
| GET    | `/devices/audit/notes/export`                   | `export_notes`       | Export notes to CSV         |
| POST   | `/devices/audit/clear`                          | `clear_audit`        | Clear audit data            |

**URLconf**: `apps/audit/urls.py`

```python
from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_home, name='home'),
    path('upload', views.upload_csv, name='upload'),
    path('session/<str:session_id>', views.view_session, name='session'),
    path('session/<str:session_id>/students', views.session_students, name='students'),
    path('student/<int:student_id>', views.student_detail, name='student'),
    path('student/<int:student_id>/devices', views.student_devices, name='devices'),
    path('student/<int:student_id>/verify', views.verify_student, name='verify'),
    path('student/<int:student_id>/re-audit', views.re_audit_student, name='re_audit'),
    path('session/<str:session_id>/completed', views.completed_students, name='completed'),
    path('notes', views.audit_notes, name='notes'),
    path('notes/export', views.export_notes, name='export'),
    path('clear', views.clear_audit, name='clear'),
]
```

---

## Students App (PROTECTED)

**App**: `apps.students`  
**URL Prefix**: `/students`  
**Authentication**: HTTP Basic Auth

| Method | URL Pattern                 | View              | Description              |
| ------ | --------------------------- | ----------------- | ------------------------ |
| GET    | `/students/student-devices` | `student_devices` | Student device lookup    |
| POST   | `/students/import`          | `import_students` | Import students from CSV |

**URLconf**: `apps/students/urls.py`

```python
from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('student-devices', views.student_devices, name='devices'),
    path('import', views.import_students, name='import'),
]
```

---

## Assets App (PROTECTED)

**App**: `apps.assets`  
**URL Prefix**: Root and `/assets`  
**Authentication**: HTTP Basic Auth

| Method | URL Pattern              | View              | Description             |
| ------ | ------------------------ | ----------------- | ----------------------- |
| GET    | `/assets/create`         | `create_asset`    | Asset creation form     |
| POST   | `/assets/create`         | `process_create`  | Create asset in RT      |
| GET    | `/next-asset-tag`        | `next_tag`        | Get next asset tag      |
| POST   | `/confirm-asset-tag`     | `confirm_tag`     | Confirm asset tag       |
| POST   | `/reset-asset-tag`       | `reset_tag`       | Reset tag sequence      |
| POST   | `/update-asset-name`     | `update_name`     | Update asset name in RT |
| POST   | `/webhook/asset-created` | `webhook_created` | RT webhook handler      |
| GET    | `/admin` (tag admin)     | `tag_admin`       | Asset tag admin page    |

**URLconf**: `apps/assets/urls.py`

```python
from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    path('create', views.create_asset, name='create'),
    # Root-level routes (registered separately in main urls.py)
]
```

**Root URLconf entries** (in `rtutils/urls.py`):

```python
# Tag management routes at root level
path('next-asset-tag', assets_views.next_tag, name='next_tag'),
path('confirm-asset-tag', assets_views.confirm_tag, name='confirm_tag'),
path('reset-asset-tag', assets_views.reset_tag, name='reset_tag'),
path('update-asset-name', assets_views.update_name, name='update_name'),
path('webhook/asset-created', assets_views.webhook_created, name='webhook'),
path('admin', assets_views.tag_admin, name='tag_admin'),
```

---

## Root URLconf

**File**: `rtutils/urls.py`

```python
from django.contrib import admin
from django.urls import path, include
from apps.assets import views as assets_views
from . import views as root_views

urlpatterns = [
    # Django admin (protected by admin auth)
    path('admin/', admin.site.urls),

    # Labels app (PUBLIC - no auth)
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
```
