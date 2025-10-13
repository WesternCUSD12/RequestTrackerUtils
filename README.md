# RequestTracker Utils

RequestTracker Utils is a comprehensive Flask-based application designed to manage student device tracking, asset tags, and seamless integration with the Request Tracker (RT) system. The application provides a complete solution for educational institutions to track device check-ins/check-outs, manage asset lifecycles, and maintain detailed audit logs.

## Architecture

This project follows a documentation-first workflow. Every feature area has an accompanying subsystem guide under [`docs/architecture/`](docs/architecture/) that captures purpose, routes, dependent utilities, configuration, and testing hooks. Start here when onboarding or researching changes:

- [Assets](docs/architecture/assets.md) – batch asset creation, name generation, and catalog caching.
- [Labels](docs/architecture/labels.md) – HTML/print label generation, barcode/QR utilities, and bulk updates.
- [Devices](docs/architecture/devices.md) – Chromebook intake workflows, CSV logging, and RT lookups.
- [Students](docs/architecture/students.md) – roster management, StudentDeviceTracker orchestration, and reconciliation flows.
- [Tags](docs/architecture/tags.md) – asset-tag sequencing, webhook ingestion, and collision safeguards.
- [Integrations](docs/architecture/integrations.md) – RT API adapters, Google Admin connectors, and scheduled sync jobs.
- [Infrastructure](docs/architecture/infrastructure.md) – runtime/deployment footprint, Nix packaging, and storage layout.

**Quick onboarding checklist:**

1. Read the subsystem guide linked above for the area you plan to touch.
2. Cross-reference the evidence snapshots (`docs/architecture/_inputs/`) to verify the current code state.
3. Follow the migration/change-set steps in [`specs/002-ensure-my-flask/quickstart.md`](specs/002-ensure-my-flask/quickstart.md) before refactoring.

## Core Features Overview

### 1. Student Device Tracking System

- **Complete device lifecycle management** with check-in/check-out workflows
- **SQLite database** with comprehensive tracking of students, devices, and transaction logs
- **Grade-based filtering and statistics** for administrative oversight
- **Manual and automatic check-in capabilities** with bulk processing support
- **CSV import/export functionality** with data validation and error handling
- **RT integration** for real-time device ownership lookup and synchronization

### 2. Asset Tag Management

- **Sequential tag generation** with configurable prefixes (default: W12-)
- **Webhook integration** for automatic tag assignment when assets are created in RT
- **Comprehensive audit logging** of all tag assignments with timestamps
- **Admin interface** for sequence management and reset capabilities
- **Batch processing** for multiple asset operations

### 3. Label Printing System

- **Professional-quality label generation** with QR codes and barcodes
- **Multiple asset lookup methods** (ID, name, query-based searching)
- **Single and batch label operations** with print-ready HTML output
- **Asset information display** including serial numbers, models, and funding sources
- **Customizable label templates** for different asset types

### 4. RT Integration & API

- **Comprehensive REST API** for all major operations
- **Real-time RT synchronization** for asset and user management
- **Device ownership tracking** with bulk operations support
- **Ticket creation** with automatic asset linking
- **User lookup capabilities** with numeric ID resolution

## Detailed Feature Documentation

### Student Device Tracking

#### Database Schema

The application uses SQLite with three core tables:

**Students Table:**

```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    grade INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Device Info Table:**

```sql
CREATE TABLE device_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_tag TEXT UNIQUE NOT NULL,
    serial_number TEXT,
    model TEXT,
    status TEXT DEFAULT 'available',
    current_student_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_student_id) REFERENCES students (student_id)
)
```

**Device Logs Table:**

```sql
CREATE TABLE device_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_tag TEXT NOT NULL,
    student_id TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (asset_tag) REFERENCES device_info (asset_tag),
    FOREIGN KEY (student_id) REFERENCES students (student_id)
)
```

#### Key Functionality

- **Check-in/Check-out Workflows**: Complete device transaction management
- **Batch Processing**: Handle multiple devices per student simultaneously
- **Grade-based Filtering**: Administrative views by grade level
- **CSV Operations**: Import student data and export transaction logs
- **RT Synchronization**: Real-time lookup of device ownership in RT system
- **Manual Override**: Administrative check-in capabilities with notes
- **Statistics Dashboard**: Grade-level and overall usage statistics

### Asset Tag Management

#### Sequential Tag Generation

- **Configurable Prefixes**: Default W12- prefix with admin customization
- **Atomic Operations**: Thread-safe tag generation with file-based sequence storage
- **Webhook Integration**: Automatic tag assignment via `/webhook/asset-created` endpoint
- **Audit Trail**: Complete logging of all tag assignments with timestamps
- **Admin Interface**: Web-based sequence management and reset capabilities

#### Webhook Functionality

```python
# Webhook endpoint for automatic tag assignment
POST /webhook/asset-created
Content-Type: application/json

{
    "asset_id": "12345",
    "asset_name": "Laptop Model X",
    "created_by": "admin_user"
}
```

### Label Printing System

#### Label Generation Capabilities

- **QR Code Integration**: Direct links to RT asset pages
- **Barcode Support**: Standard barcode generation for asset tags
- **Professional Layout**: Print-ready HTML with CSS styling
- **Asset Information Display**: Serial numbers, models, funding sources
- **Batch Operations**: Multiple labels with one per page formatting

#### API Endpoints

```python
# Single label generation
GET /labels/print?asset_id=12345

# Batch label generation
POST /labels/batch
Content-Type: application/json
{
    "asset_ids": ["12345", "12346", "12347"]
}

# Debug label information
GET /labels/debug?asset_id=12345
```

## Complete API Reference

### Student Management API

- `GET /api/students` - List all students with optional grade filtering
- `POST /api/students` - Create new student record
- `DELETE /api/students/{student_id}` - Remove student record
- `GET /api/students/{student_id}/devices` - Get devices assigned to student
- `POST /api/students/{student_id}/checkin` - Check-in device to student
- `POST /api/students/{student_id}/checkout` - Check-out device from student

### Device Management API

- `GET /api/devices` - List all devices with status filtering
- `POST /api/devices` - Register new device
- `PUT /api/devices/{asset_tag}` - Update device information
- `GET /api/devices/{asset_tag}/history` - Get device transaction history
- `POST /api/devices/batch-checkin` - Bulk device check-in operations

### RT Integration API

- `GET /api/rt-lookup/student/{id}` - Lookup student devices in RT
- `POST /api/rt-lookup/batch` - Batch device ownership lookup
- `GET /api/rt-lookup/user/{username}` - RT user information lookup
- `POST /api/tickets/create` - Create RT ticket with asset linking

### Asset Tag API

- `GET /next-asset-tag` - Generate next sequential asset tag
- `POST /confirm-asset-tag` - Confirm and assign asset tag
- `POST /webhook/asset-created` - Webhook for automatic tag assignment
- `GET /admin/asset-tags` - Asset tag administration interface

### Label Generation API

- `GET /labels/print` - Generate single asset label
- `POST /labels/batch` - Generate multiple asset labels
- `GET /labels/debug` - Debug asset label information

## Installation & Configuration

### Requirements

````
Python >= 3.11
Flask >= 2.2.0
requests >= 2.28.0
qrcode >= 7.3.1
python-barcode >= 0.13.1
### Environment Variables Configuration
```bash
# RT Configuration
export RT_URL="https://your-rt-instance.com"
export RT_TOKEN="your-rt-api-token"
export API_ENDPOINT="/REST/2.0"

# Asset Tag Configuration
export PREFIX="W12-"  # Default asset tag prefix
export ASSET_TAG_SEQUENCE_FILE="asset_tag_sequence.txt"

# Database Configuration
export DATABASE_PATH="instance/database.sqlite"

# Label Configuration
export LABEL_TEMPLATE_PATH="templates/label.html"

# Logging Configuration
export LOG_LEVEL="INFO"
export LOG_FILE="instance/logs/app.log"
````

### Installation Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/WesternCUSD12/RequestTrackerUtils.git
   cd RequestTrackerUtils
   ```

2. **Install dependencies:**

   ```bash
   pip install -e .
   ```

3. **Configure environment variables** (see above)

4. **Initialize database:**

   ```bash
   python -c "from request_tracker_utils.utils.db import init_db; init_db()"
   ```

5. **Run the application:**
   ```bash
   python run.py
   ```

### Using Nix Development Environment

This project includes a `flake.nix` for reproducible development environments:

```bash
nix develop
# OR
devenv shell
python run.py
```

## Usage Examples

### Student Device Check-in Workflow

```bash
# Check-in device to student
curl -X POST http://localhost:8080/api/students/12345/checkin \
  -H "Content-Type: application/json" \
  -d '{"asset_tag": "W12-1001", "notes": "Device assignment"}'

# Check-out device from student
curl -X POST http://localhost:8080/api/students/12345/checkout \
  -H "Content-Type: application/json" \
  -d '{"asset_tag": "W12-1001", "notes": "Device return"}'
```

### Asset Tag Management

```bash
# Get next asset tag
curl http://localhost:8080/next-asset-tag

# Confirm asset tag assignment
curl -X POST http://localhost:8080/confirm-asset-tag \
  -H "Content-Type: application/json" \
  -d '{"asset_tag": "W12-1025", "request_tracker_id": 12345}'
```

### Label Generation

```bash
# Generate single label
curl "http://localhost:8080/labels/print?assetId=12345"

# Generate batch labels
curl -X POST http://localhost:8080/labels/batch \
  -H "Content-Type: application/json" \
  -d '{"asset_ids": ["12345", "12346", "12347"]}'
```

## Webhook Configuration

### RT Webhook Setup

Configure Request Tracker to automatically assign asset tags:

1. **Create Scrip in RT Admin:**

   - Condition: "On Create"
   - Action: "User Defined"
   - Template: "Blank"

2. **Custom Action Code:**

   ```perl
   my $asset = $self->TicketObj;
   my $webhook_url = "http://your-app-url/webhook/asset-created";

   my $data = {
       asset_id => $asset->Id,
       event => "create",
       timestamp => time()
   };

   # Send webhook request
   use LWP::UserAgent;
   use JSON;

   my $ua = LWP::UserAgent->new;
   my $response = $ua->post(
       $webhook_url,
       Content_Type => 'application/json',
       Content => encode_json($data)
   );
   ```

## Recreating This Application in Django

This section provides comprehensive instructions for recreating the RequestTracker Utils functionality using Django.

### Django Project Structure

```
rtutils_django/
├── manage.py
├── requirements.txt
├── rtutils/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py
│   └── migrations/
├── students/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py
│   └── admin.py
├── devices/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── serializers.py
├── assets/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── serializers.py
├── labels/
│   ├── __init__.py
│   ├── views.py
│   ├── urls.py
│   └── utils.py
├── rt_integration/
│   ├── __init__.py
│   ├── api.py
│   ├── webhooks.py
│   └── utils.py
└── templates/
    ├── base.html
    ├── students/
    ├── devices/
    ├── labels/
    └── admin/
```

### Django Models Implementation

#### 1. Student Models (`students/models.py`)

```python
from django.db import models
from django.utils import timezone

class Student(models.Model):
    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    grade = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'students'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_current_devices(self):
        return Device.objects.filter(current_student=self, status='checked_out')
```

#### 2. Device Models (`devices/models.py`)

```python
from django.db import models
from django.utils import timezone
from students.models import Student

class Device(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('checked_out', 'Checked Out'),
        ('maintenance', 'Maintenance'),
        ('retired', 'Retired'),
    ]

    asset_tag = models.CharField(max_length=20, unique=True)
    serial_number = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    current_student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'device_info'
        ordering = ['asset_tag']

    def __str__(self):
        return f"{self.asset_tag} - {self.model}"

    def check_in_to_student(self, student, notes=""):
        """Check device in to a student"""
        self.current_student = student
        self.status = 'checked_out'
        self.save()

        # Create log entry
        DeviceLog.objects.create(
            device=self,
            student=student,
            action='check_in',
            notes=notes
        )

    def check_out_from_student(self, notes=""):
        """Check device out from current student"""
        if self.current_student:
            # Create log entry
            DeviceLog.objects.create(
                device=self,
                student=self.current_student,
                action='check_out',
                notes=notes
            )

        self.current_student = None
        self.status = 'available'
        self.save()

class DeviceLog(models.Model):
    ACTION_CHOICES = [
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
        ('maintenance', 'Maintenance'),
        ('repair', 'Repair'),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='logs')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='device_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'device_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.device.asset_tag} - {self.action} - {self.student.full_name}"
```

#### 3. Asset Tag Models (`assets/models.py`)

```python
from django.db import models
from django.utils import timezone
from django.core.cache import cache
import threading

class AssetTagSequence(models.Model):
    prefix = models.CharField(max_length=10, default='W12-')
    current_number = models.IntegerField(default=1)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asset_tag_sequence'

    @classmethod
    def get_next_tag(cls):
        """Thread-safe method to get next asset tag"""
        with threading.Lock():
            sequence, created = cls.objects.get_or_create(
                id=1,
                defaults={'prefix': 'W12-', 'current_number': 1}
            )

            next_tag = f"{sequence.prefix}{sequence.current_number:04d}"
            return next_tag

    @classmethod
    def confirm_tag_assignment(cls, tag, rt_asset_id):
        """Confirm tag assignment and increment sequence"""
        with threading.Lock():
            sequence = cls.objects.get(id=1)
            sequence.current_number += 1
            sequence.save()

            # Create audit log
            AssetTagAudit.objects.create(
                asset_tag=tag,
                rt_asset_id=rt_asset_id,
                action='assigned'
            )

class AssetTagAudit(models.Model):
    asset_tag = models.CharField(max_length=20)
    rt_asset_id = models.IntegerField()
    action = models.CharField(max_length=20)
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'asset_tag_audit'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.asset_tag} - {self.action} - {self.timestamp}"
```

### Django Views Implementation

#### 1. Student API Views (`students/views.py`)

```python
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Student
from .serializers import StudentSerializer
from devices.models import Device

class StudentListCreateView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        queryset = Student.objects.all()
        grade = self.request.query_params.get('grade')
        if grade:
            queryset = queryset.filter(grade=grade)
        return queryset

class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    lookup_field = 'student_id'

@api_view(['POST'])
def student_checkin(request, student_id):
    """Check-in device to student"""
    student = get_object_or_404(Student, student_id=student_id)
    asset_tag = request.data.get('asset_tag')
    notes = request.data.get('notes', '')

    if not asset_tag:
        return Response({'error': 'asset_tag is required'},
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        device = Device.objects.get(asset_tag=asset_tag)
        if device.status != 'available':
            return Response({'error': 'Device is not available'},
                           status=status.HTTP_400_BAD_REQUEST)

        device.check_in_to_student(student, notes)

        return Response({
            'message': f'Device {asset_tag} checked in to {student.full_name}',
            'student': student.student_id,
            'device': asset_tag,
            'status': 'checked_in'
        })

    except Device.DoesNotExist:
        return Response({'error': 'Device not found'},
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def student_checkout(request, student_id):
    """Check-out device from student"""
    student = get_object_or_404(Student, student_id=student_id)
    asset_tag = request.data.get('asset_tag')
    notes = request.data.get('notes', '')

    if not asset_tag:
        return Response({'error': 'asset_tag is required'},
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        device = Device.objects.get(asset_tag=asset_tag, current_student=student)
        device.check_out_from_student(notes)

        return Response({
            'message': f'Device {asset_tag} checked out from {student.full_name}',
            'student': student.student_id,
            'device': asset_tag,
            'status': 'checked_out'
        })

    except Device.DoesNotExist:
        return Response({'error': 'Device not found or not assigned to student'},
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def student_devices(request, student_id):
    """Get all devices currently assigned to student"""
    student = get_object_or_404(Student, student_id=student_id)
    devices = student.get_current_devices()

    device_data = [{
        'asset_tag': device.asset_tag,
        'model': device.model,
        'serial_number': device.serial_number,
        'status': device.status,
        'checked_in_date': device.logs.filter(action='check_in').first().timestamp
    } for device in devices]

    return Response({
        'student': student.full_name,
        'student_id': student.student_id,
        'grade': student.grade,
        'devices': device_data,
        'device_count': len(device_data)
    })
```

#### 2. Device API Views (`devices/views.py`)

```python
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Device, DeviceLog
from .serializers import DeviceSerializer, DeviceLogSerializer

class DeviceListCreateView(generics.ListCreateAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

    def get_queryset(self):
        queryset = Device.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    lookup_field = 'asset_tag'

@api_view(['GET'])
def device_history(request, asset_tag):
    """Get transaction history for a device"""
    device = get_object_or_404(Device, asset_tag=asset_tag)
    logs = DeviceLog.objects.filter(device=device)
    serializer = DeviceLogSerializer(logs, many=True)

    return Response({
        'device': asset_tag,
        'model': device.model,
        'current_status': device.status,
        'current_student': device.current_student.full_name if device.current_student else None,
        'history': serializer.data
    })

@api_view(['POST'])
def batch_checkin(request):
    """Batch check-in multiple devices"""
    operations = request.data.get('operations', [])
    results = []

    for operation in operations:
        student_id = operation.get('student_id')
        asset_tag = operation.get('asset_tag')
        notes = operation.get('notes', '')

        try:
            student = Student.objects.get(student_id=student_id)
            device = Device.objects.get(asset_tag=asset_tag)

            if device.status == 'available':
                device.check_in_to_student(student, notes)
                results.append({
                    'asset_tag': asset_tag,
                    'student_id': student_id,
                    'status': 'success',
                    'message': 'Device checked in successfully'
                })
            else:
                results.append({
                    'asset_tag': asset_tag,
                    'student_id': student_id,
                    'status': 'error',
                    'message': 'Device not available'
                })

        except (Student.DoesNotExist, Device.DoesNotExist) as e:
            results.append({
                'asset_tag': asset_tag,
                'student_id': student_id,
                'status': 'error',
                'message': str(e)
            })

    return Response({
        'batch_operation': 'checkin',
        'total_operations': len(operations),
        'results': results
    })
```

#### 3. Asset Tag API Views (`assets/views.py`)

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import AssetTagSequence, AssetTagAudit
from rt_integration.api import RTApiClient

@api_view(['GET'])
def next_asset_tag(request):
    """Get next available asset tag without incrementing sequence"""
    next_tag = AssetTagSequence.get_next_tag()
    return Response({'next_asset_tag': next_tag})

@api_view(['POST'])
def confirm_asset_tag(request):
    """Confirm asset tag assignment and update RT"""
    asset_tag = request.data.get('asset_tag')
    rt_asset_id = request.data.get('request_tracker_id')

    if not asset_tag or not rt_asset_id:
        return Response(
            {'error': 'asset_tag and request_tracker_id are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Update asset name in RT
        rt_client = RTApiClient()
        rt_client.update_asset_name(rt_asset_id, asset_tag)

        # Confirm tag assignment
        AssetTagSequence.confirm_tag_assignment(asset_tag, rt_asset_id)

        return Response({
            'message': 'Asset tag confirmation logged successfully. Asset name updated in RT.',
            'asset_tag': asset_tag,
            'rt_asset_id': rt_asset_id
        })

    except Exception as e:
        return Response(
            {'error': f'Failed to update asset: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def webhook_asset_created(request):
    """Webhook endpoint for automatic asset tag assignment"""
    asset_id = request.data.get('asset_id')

    if not asset_id:
        return Response(
            {'error': 'asset_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get next asset tag
        next_tag = AssetTagSequence.get_next_tag()

        # Update asset name in RT
        rt_client = RTApiClient()
        old_name = rt_client.get_asset_name(asset_id)
        rt_client.update_asset_name(asset_id, next_tag)

        # Confirm tag assignment
        AssetTagSequence.confirm_tag_assignment(next_tag, asset_id)

        return Response({
            'message': f'Asset tag {next_tag} assigned to asset {asset_id}',
            'asset_id': asset_id,
            'asset_tag': next_tag,
            'previous_name': old_name
        })

    except Exception as e:
        return Response(
            {'error': f'Failed to assign asset tag: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

#### 4. Label Generation Views (`labels/views.py`)

```python
from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import LabelGenerator
from rt_integration.api import RTApiClient
import qrcode
import io
import base64

@api_view(['GET'])
def print_label(request):
    """Generate single asset label"""
    asset_id = request.GET.get('assetId')
    asset_name = request.GET.get('assetName')

    if not asset_id and not asset_name:
        return Response({'error': 'assetId or assetName is required'})

    try:
        rt_client = RTApiClient()

        if asset_name:
            asset_id = rt_client.get_asset_id_by_name(asset_name)

        asset_data = rt_client.get_asset_details(asset_id)

        # Generate QR code
        qr_data = f"{rt_client.base_url}/Asset/Display.html?id={asset_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()

        # Generate barcode
        barcode_generator = LabelGenerator()
        barcode_base64 = barcode_generator.generate_barcode(asset_data['Name'])

        context = {
            'asset': asset_data,
            'qr_code': qr_base64,
            'barcode': barcode_base64,
            'rt_url': f"{rt_client.base_url}/Asset/Display.html?id={asset_id}"
        }

        return render(request, 'labels/label.html', context)

    except Exception as e:
        return Response({'error': str(e)})

@api_view(['GET', 'POST'])
def batch_labels(request):
    """Generate batch labels"""
    if request.method == 'GET':
        return render(request, 'labels/batch_form.html')

    asset_ids = request.data.get('asset_ids', [])
    query = request.data.get('query')

    if query:
        rt_client = RTApiClient()
        asset_ids = rt_client.search_assets(query)

    if not asset_ids:
        return Response({'error': 'No assets found'})

    try:
        rt_client = RTApiClient()
        assets = []

        for asset_id in asset_ids:
            asset_data = rt_client.get_asset_details(asset_id)

            # Generate QR code
            qr_data = f"{rt_client.base_url}/Asset/Display.html?id={asset_id}"
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()

            # Generate barcode
            barcode_generator = LabelGenerator()
            barcode_base64 = barcode_generator.generate_barcode(asset_data['Name'])

            assets.append({
                'data': asset_data,
                'qr_code': qr_base64,
                'barcode': barcode_base64,
                'rt_url': f"{rt_client.base_url}/Asset/Display.html?id={asset_id}"
            })

        context = {'assets': assets}
        return render(request, 'labels/batch_labels.html', context)

    except Exception as e:
        return Response({'error': str(e)})
```

### Django Settings Configuration

#### Main Settings (`rtutils/settings.py`)

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-secret-key-here')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'core',
    'students',
    'devices',
    'assets',
    'labels',
    'rt_integration',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rtutils.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'instance' / 'database.sqlite',
    }
}

# RT Configuration
RT_URL = os.environ.get('RT_URL', 'https://your-rt-instance.com')
RT_TOKEN = os.environ.get('RT_TOKEN', '')
RT_API_ENDPOINT = os.environ.get('API_ENDPOINT', '/REST/2.0')

# Asset Tag Configuration
ASSET_TAG_PREFIX = os.environ.get('PREFIX', 'W12-')
ASSET_TAG_SEQUENCE_FILE = os.environ.get('ASSET_TAG_SEQUENCE_FILE', 'asset_tag_sequence.txt')

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'instance' / 'logs' / 'django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
}

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
```

### Django URL Configuration

#### Main URLs (`rtutils/urls.py`)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/students/', include('students.urls')),
    path('api/devices/', include('devices.urls')),
    path('api/', include('assets.urls')),
    path('labels/', include('labels.urls')),
    path('webhook/', include('rt_integration.urls')),
    path('', include('core.urls')),
]
```

#### Student URLs (`students/urls.py`)

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.StudentListCreateView.as_view(), name='student-list-create'),
    path('<str:student_id>/', views.StudentDetailView.as_view(), name='student-detail'),
    path('<str:student_id>/checkin/', views.student_checkin, name='student-checkin'),
    path('<str:student_id>/checkout/', views.student_checkout, name='student-checkout'),
    path('<str:student_id>/devices/', views.student_devices, name='student-devices'),
]
```

### Django Requirements (`requirements.txt`)

```
Django>=4.2.0
djangorestframework>=3.14.0
django-cors-headers>=4.0.0
requests>=2.28.0
qrcode>=7.3.1
python-barcode>=0.13.1
Pillow>=9.0.0
celery>=5.2.0
redis>=4.5.0
```

### Django Management Commands

#### Initialize Database (`core/management/commands/init_db.py`)

```python
from django.core.management.base import BaseCommand
from django.db import connection
from students.models import Student
from devices.models import Device, DeviceLog
from assets.models import AssetTagSequence, AssetTagAudit

class Command(BaseCommand):
    help = 'Initialize database with required tables and data'

    def handle(self, *args, **options):
        # Create tables (Django migrations handle this)
        self.stdout.write('Creating database tables...')

        # Initialize asset tag sequence
        AssetTagSequence.objects.get_or_create(
            id=1,
            defaults={'prefix': 'W12-', 'current_number': 1}
        )

        self.stdout.write(
            self.style.SUCCESS('Database initialized successfully')
        )
```

### Django Migration Strategy

1. **Initial Migration:**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Data Migration from Flask:**

   ```python
   # management/commands/migrate_from_flask.py
   from django.core.management.base import BaseCommand
   import sqlite3
   from students.models import Student
   from devices.models import Device, DeviceLog

   class Command(BaseCommand):
       def handle(self, *args, **options):
           # Connect to Flask SQLite database
           flask_db = sqlite3.connect('instance/database.sqlite')
           cursor = flask_db.cursor()

           # Migrate students
           cursor.execute('SELECT * FROM students')
           for row in cursor.fetchall():
               Student.objects.get_or_create(
                   student_id=row[1],
                   defaults={
                       'first_name': row[2],
                       'last_name': row[3],
                       'grade': row[4],
                   }
               )

           # Migrate devices and logs similarly...
   ```

### Django Deployment Considerations

#### Production Settings (`rtutils/settings_prod.py`)

```python
from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# Use PostgreSQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Use Redis for caching and Celery
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

### Django vs Flask Feature Comparison

| Feature         | Flask Implementation  | Django Implementation       |
| --------------- | --------------------- | --------------------------- |
| Database ORM    | SQLAlchemy or raw SQL | Django ORM with Models      |
| API Framework   | Flask-RESTful         | Django REST Framework       |
| Admin Interface | Custom HTML templates | Django Admin + custom views |
| Authentication  | Flask-Login           | Django Auth system          |
| Task Queue      | Manual implementation | Celery integration          |
| URL Routing     | Flask blueprints      | Django URL patterns         |
| Templates       | Jinja2                | Django templates            |
| Migrations      | Manual SQL scripts    | Django migrations           |
| Configuration   | Environment variables | Django settings             |
| Testing         | unittest/pytest       | Django TestCase             |

### Migration Timeline

1. **Phase 1: Core Models** (Week 1)

   - Set up Django project structure
   - Implement Student, Device, DeviceLog models
   - Create basic API endpoints

2. **Phase 2: Asset Management** (Week 2)

   - Implement AssetTagSequence and AssetTagAudit models
   - Add asset tag generation API
   - Set up webhook endpoints

3. **Phase 3: Label Generation** (Week 3)

   - Implement label generation views
   - Create Django templates for labels
   - Add batch processing capabilities

4. **Phase 4: RT Integration** (Week 4)

   - Port RT API client to Django
   - Implement RT integration views
   - Add comprehensive error handling

5. **Phase 5: Data Migration** (Week 5)
   - Create migration scripts from Flask SQLite
   - Test data integrity
   - Deploy to production environment

This comprehensive Django implementation maintains all the functionality of the original Flask application while leveraging Django's robust features for scalability, maintainability, and developer productivity.

- Description: Auto Asset Tag Assignment
- Condition: On Create
- Stage: TransactionCreate
- Action: User Defined
- Template: User Defined

3. In the Custom Condition code, add:

```perl
return 1 if $self->TransactionObj->Type eq 'Create' && $self->TransactionObj->ObjectType eq 'RT::Asset';
return 0;
```

4. In the Custom Action code, add:

```perl
use LWP::UserAgent;
use JSON;
use HTTP::Request;

my $asset_id = $self->TransactionObj->ObjectId;
my $webhook_url = 'http://your-server-address/webhook/asset-created';

# Get the asset object to modify it later
my $asset = RT::Asset->new($RT::SystemUser);
$asset->Load($asset_id);

# Use eval for error handling
eval {
  # Create a user agent for making HTTP requests
  my $ua = LWP::UserAgent->new(timeout => 10);

  # Send POST request to the webhook with the asset ID
  my $response = $ua->post(
    $webhook_url,
    'Content-Type' => 'application/json',
    'Content' => encode_json({
      asset_id => $asset_id,
      event => 'create',
      timestamp => time()
    })
  );

  # Check if the request was successful
  if ($response->is_success) {
    # Parse the JSON response
    my $result = decode_json($response->decoded_content);

    # If the webhook assigned a tag, update the asset name in RT
    if ($result->{asset_tag}) {
      my $new_tag = $result->{asset_tag};

      # Update the asset's name
      $RT::Logger->info("Updating asset #$asset_id name to '$new_tag'");
      $asset->SetName($new_tag);

      # Log the result
      $RT::Logger->info("Asset #$asset_id name updated to: " . $asset->Name);
    } else {
      $RT::Logger->warning("No asset tag received from webhook for asset #$asset_id");
    }
  } else {
    # Log the error if the webhook request failed
    $RT::Logger->error("Webhook request failed: " . $response->status_line);
    $RT::Logger->error("Response content: " . $response->decoded_content);
  }
};
if ($@) {
  # Catch any exceptions and log them
  $RT::Logger->error("Error in asset creation webhook: $@");
}

# Return success regardless of webhook result to avoid affecting RT
return 1;
```

5. Apply to: Assets
6. Set appropriate Queue/Catalog restrictions if needed
7. Save the Scrip

**Note:** Be sure to replace 'http://your-server-address' with your actual server URL.

---

## NixOS Service Module

This project includes a NixOS service module for deploying the Flask app as a systemd service.

### Configuration Options

| Option        | Type   | Default                                    | Description                           |
| ------------- | ------ | ------------------------------------------ | ------------------------------------- |
| `enable`      | bool   | `false`                                    | Enable the Flask app service.         |
| `host`        | string | `"127.0.0.1"`                              | Host address for the Flask app.       |
| `port`        | int    | `5000`                                     | Port for the Flask app.               |
| `secretsFile` | path   | `"/etc/request-tracker-utils/secrets.env"` | Path to the secrets environment file. |

### Example Configuration

To use this module via a Nix flake, add the following to your `flake.nix`:

```nix
{
   inputs = {
      nixpkgs.url = "github:NixOS/nixpkgs";
      request-tracker-utils.url = "github:WesternCUSD12/RequestTrackerUtils";
   };

   outputs = { self, nixpkgs, request-tracker-utils }: {
      nixosConfigurations.mySystem = nixpkgs.lib.nixosSystem {
         system = "x86_64-linux";
         modules = [
            ./hardware-configuration.nix
            request-tracker-utils.nixosModule
            {
               services.requestTrackerUtils = {
                  enable = true;
                  host = "0.0.0.0";
                  port = 8080;
                  secretsFile = "/run/secrets/request-tracker-utils.env";
               };
            }
         ];
      };
   };
}
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
