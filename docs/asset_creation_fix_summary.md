# RT Asset Creation Fix - Troubleshooting Summary

## Problem

Assets were being created in the Student Devices catalog, but custom fields (Serial Number, Manufacturer, Model, Internal Name, Category, Funding Source) were not being populated.

## Root Cause

The code was using the **wrong format** for setting custom fields in RT's REST2 API.

### Incorrect Format (What we were using)

```python
asset_data = {
    'Name': 'TEST-0001',
    'Catalog': 'Student Devices',
    'CF.{Serial Number}': 'ABC123',  # ❌ Wrong!
    'CF.{Manufacturer}': 'Apple',     # ❌ Wrong!
    # ... etc
}
```

### Correct Format (Per RT REST2 API Documentation)

Per the [RT REST2 API documentation](https://docs.bestpractical.com/rt/6.0.1/RT/REST2.html#Object-Custom-Field-Values):

**For single-value custom fields**: Use a JSON object with field names as keys and string values
**For multi-value custom fields**: Use a JSON object with field names as keys and array values

```python
# Step 1: Create the asset with basic fields
asset_data = {
    'Name': 'TEST-0001',
    'Catalog': 'Student Devices',
    'Description': 'Asset description'
}
response = rt_api_request('POST', '/asset', data=asset_data, config=config)
asset_id = response.get('id')

# Step 2: Update with custom fields
custom_fields_data = {
    'CustomFields': {
        'Serial Number': 'ABC123',      # ✅ Correct! (single-value)
        'Manufacturer': 'Apple',         # ✅ Correct! (single-value)
        'Model': 'MacBook Air',          # ✅ Correct! (single-value)
        'Internal Name': 'Happy Panda',  # ✅ Correct! (single-value)
        'Multi Field': ['val1', 'val2']  # ✅ Correct! (multi-value)
    }
}
rt_api_request('PUT', f'/asset/{asset_id}', data=custom_fields_data, config=config)
```

## Solution Implemented

Updated `/Users/jmartin/rtutils/request_tracker_utils/routes/asset_routes.py` to:

1. **Create asset** with basic fields (Name, Catalog, Description) first
2. **Update asset** with custom fields using the correct CustomFields object format

### Changes Made

**Before:**

```python
asset_data = {
    'Name': asset_tag,
    'Catalog': catalog,
    'CF.{Serial Number}': serial_number,  # Wrong format
    'CF.{Manufacturer}': manufacturer,    # Wrong format
    # ...
}
response = rt_api_request('POST', '/asset', data=asset_data, config=current_app.config)
```

**After:**

```python
# Step 1: Create with basic fields
asset_data = {
    'Name': asset_tag,
    'Catalog': catalog,
    'Description': f'Asset {asset_tag} - {internal_name}'
}
response = rt_api_request('POST', '/asset', data=asset_data, config=current_app.config)
asset_id = response.get('id')

# Step 2: Update with custom fields (correct format)
custom_fields = {
    'Serial Number': serial_number,
    'Manufacturer': manufacturer,
    'Model': model,
    'Internal Name': internal_name
}
if data.get('category'):
    custom_fields['Category'] = data.get('category')
if data.get('funding_source'):
    custom_fields['Funding Source'] = data.get('funding_source')

custom_fields_data = {'CustomFields': custom_fields}
rt_api_request('PUT', f'/asset/{asset_id}', data=custom_fields_data, config=current_app.config)
```

## Test Results

Created test asset `TEST-0002` (ID: 2242) successfully with all fields populated:

- ✅ Serial Number: `TEST-SERIAL-TEST-0002`
- ✅ Manufacturer: `Apple`
- ✅ Model: `Test MacBook Air`
- ✅ Internal Name: `Esteemed Finch`

## Additional Findings

1. **Invalid Status Error**: Initially tried to set `Status: 'allocated'` which caused a 400 error. RT returned: `"Status 'allocated' isn't a valid status for assets."` - Removed this field.

2. **Field Name Mappings for Student Devices Catalog**:

   - Form field `category` → RT custom field **`Type`** (ID 6) ✅ Working
   - Form field `funding_source` → RT custom field **`Funding Source`** (ID 3) - needs verification

3. **Two-Step Process Required**: Custom fields cannot be set during asset creation (POST), they must be updated afterwards (PUT).

4. **Successful Test Results**: TEST-0003 (Asset ID 2243) created with all core fields populated:
   - Serial Number: `TEST-SERIAL-TEST-0003`
   - Manufacturer: `Apple`
   - Model: `Test MacBook Air`
   - Internal Name: `Metallic Wildebeest`
   - Type: `Chromebook`

## References

- [RT REST2 API Documentation - Object Custom Field Values](https://docs.bestpractical.com/rt/6.0.1/RT/REST2.html#Object-Custom-Field-Values)
- [RT REST2 API Documentation - Assets](https://docs.bestpractical.com/rt/6.0.1/RT/REST2.html#Assets)

## Date

October 10, 2025
