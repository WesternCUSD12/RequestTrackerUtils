from django import forms
from django.core.exceptions import ValidationError


class DeviceCheckInForm(forms.Form):
    """
    Form for device check-in via asset tag/name lookup.
    
    Used by tech staff to check in devices during collection season.
    Validates asset tag input and triggers student status update.
    """
    
    asset_tag = forms.CharField(
        label='Asset Tag',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Scan or enter asset tag (e.g., W12-0123)',
            'autofocus': 'autofocus',
            'autocomplete': 'off',
        }),
        help_text='Scan device barcode or enter asset tag manually'
    )
    
    confirm_recheck = forms.BooleanField(
        label='Confirm re-check-in',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        help_text='Check this box to confirm re-checking in a device that was already checked in'
    )
    
    def clean_asset_tag(self):
        """Validate asset tag is not empty and properly formatted."""
        asset_tag = self.cleaned_data.get('asset_tag', '').strip()
        
        if not asset_tag:
            raise ValidationError('Asset tag cannot be empty')
        
        if len(asset_tag) < 3:
            raise ValidationError('Asset tag must be at least 3 characters')
        
        return asset_tag
