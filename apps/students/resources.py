"""Django import-export resources for Student model CSV import/export."""

from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Student


class StudentResource(resources.ModelResource):
    """Resource for importing and exporting student data via CSV."""

    student_id = fields.Field(
        column_name='student_id',
        attribute='student_id'
    )
    first_name = fields.Field(
        column_name='first_name',
        attribute='first_name'
    )
    last_name = fields.Field(
        column_name='last_name',
        attribute='last_name'
    )
    grade = fields.Field(
        column_name='grade',
        attribute='grade'
    )
    advisor = fields.Field(
        column_name='advisor',
        attribute='advisor'
    )
    username = fields.Field(
        column_name='username',
        attribute='username'
    )

    class Meta:
        model = Student
        fields = ('student_id', 'first_name', 'last_name', 'username', 'grade', 'advisor')
        import_id_fields = ['student_id']  # Use student_id for upsert matching
        skip_unchanged = False
        report_skipped = True

    def before_import(self, dataset, **kwargs):
        """Mark all existing students as inactive before import (FR-004a)."""
        dry_run = kwargs.get('dry_run', False)
        if not dry_run:
            # Only mark as inactive if there are rows to import
            if len(dataset) > 0:
                Student.objects.all().update(is_active=False)

    def before_import_row(self, row, row_number, **kwargs):
        """Validate required columns before processing each row (FR-005)."""
        required_columns = ['student_id', 'first_name', 'last_name', 'grade', 'username']
        optional_columns = ['advisor']  # Advisor can be blank
        
        # Check required columns are not empty
        for col in required_columns:
            if col not in row or not row[col] or str(row[col]).strip() == '':
                raise ValueError(
                    f"Row {row_number}: Missing or empty required column '{col}'. "
                    f"Required columns: {', '.join(required_columns)}"
                )
        
        # Validate grade is a number
        try:
            int(row['grade'])
        except (ValueError, TypeError):
            raise ValueError(
                f"Row {row_number}: Invalid grade value '{row['grade']}'. Grade must be a number (0-12)."
            )

    def after_save_instance(self, instance, row, **kwargs):
        """Mark imported students as active (FR-004a)."""
        instance.is_active = True
        instance.save()

    def skip_row(self, instance, original, row, import_data_row, **kwargs):
        """Override to ensure no rows are skipped unless truly empty."""
        # Don't skip any rows - we want to process all valid data
        return False

    def get_import_id_fields(self):
        """Get the fields to match on for updates."""
        return self.Meta.import_id_fields
