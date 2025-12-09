# Generated migration for audit device verification

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0003_auditsession_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditdevicerecord',
            name='asset_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='auditdevicerecord',
            name='model_number',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='auditdevicerecord',
            name='audit_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('correct', 'Correct'), ('extra', 'Extra Device'), ('other', 'Other')],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='auditdevicerecord',
            name='audit_notes',
            field=models.TextField(blank=True, help_text='Notes about device condition or discrepancies'),
        ),
        migrations.AddField(
            model_name='auditdevicerecord',
            name='verified_by',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name='AuditChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_name', models.CharField(help_text='Teacher or admin who made the change', max_length=255)),
                ('action', models.CharField(
                    choices=[
                        ('device_status_changed', 'Device Status Changed'),
                        ('device_notes_added', 'Device Notes Added'),
                        ('device_notes_updated', 'Device Notes Updated'),
                        ('student_audit_completed', 'Student Audit Completed'),
                        ('session_locked', 'Session Locked'),
                        ('session_unlocked', 'Session Unlocked'),
                    ],
                    max_length=50,
                )),
                ('device_info', models.CharField(blank=True, help_text='Device asset ID/tag for quick reference', max_length=255)),
                ('old_value', models.TextField(blank=True, help_text='Previous value')),
                ('new_value', models.TextField(blank=True, help_text='New value')),
                ('notes', models.TextField(blank=True, help_text='Additional context about the change')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_logs', to='audit.auditsession', to_field='session_id')),
                ('audit_student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_logs', to='audit.auditstudent')),
                ('device_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_logs', to='audit.auditdevicerecord')),
            ],
            options={
                'db_table': 'audit_change_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditchangelog',
            index=models.Index(fields=['session', '-timestamp'], name='audit_chang_session_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='auditchangelog',
            index=models.Index(fields=['audit_student', '-timestamp'], name='audit_chang_student_timestamp_idx'),
        ),
    ]
