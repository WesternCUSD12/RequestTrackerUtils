# Small Label Template Quick Start

## Overview

This guide explains how to use the new small label template (1.1" x 3.5" / 29mm x 90.3mm) for compact asset labels, primarily for chargers and accessories.

---

## When to Use Small Labels

### Recommended For:

- ✅ **Chargers** (Chromebook chargers, USB-C adapters)
- ✅ **Power adapters** (wall warts, power bricks)
- ✅ **Cables** (USB-C cables, HDMI cables)
- ✅ **Small accessories** (dongles, adapters, styluses)

### Use Large Labels For:

- 📱 **Chromebooks** (need serial number for tracking)
- 📱 **Hotspots** (benefit from larger QR codes)
- 📱 **High-value devices** (iPads, laptops, etc.)

### Default Behavior:

The system automatically pre-selects the appropriate label size based on asset type:

- Assets with Type = "Charger", "Power Adapter", or "Cable" → **Small label** selected by default
- All other assets → **Large label** selected by default

_You can always override the default by manually selecting a different size._

---

## How to Print a Small Label

### Method 1: Via Web Interface (Recommended)

1. **Navigate to Asset Details**

   - Go to Request Tracker asset page (e.g., `/asset/12345`)
   - Or search for asset by name in RT search

2. **Access Label Print Form**

   - Click **"Print Label"** button in asset actions menu
   - Or navigate directly to `/labels/print?id=12345`

3. **Select Label Size**

   - Form displays two radio button options:
     ```
     ○ Large Label (100mm x 62mm) - Default for Chromebooks
     ● Small Label (29mm x 90.3mm) - Default for Chargers
     ```
   - Correct size is pre-selected based on asset type
   - Change selection if needed

4. **Preview Label**

   - Click **"Preview"** button
   - Browser opens print preview with actual-size rendering
   - Check for:
     - ✅ QR code scannable (test with phone or scanner)
     - ✅ Asset name readable (may be truncated if long)
     - ✅ Barcode scannable (test with handheld scanner)
   - **Warning indicators**:
     - 🟡 "Asset name truncated" (if name > 60mm width)
     - 🔴 "QR code may be unscannable" (if URL too long for small QR)

5. **Print or Export**
   - **Print**: Click browser's Print button → select thermal label printer → print
   - **Export PDF**: Click **"Download PDF"** button → save for batch printing

---

### Method 2: Direct URL (Power Users)

**Print Small Label by Asset ID**:

```
https://rt.yourdomain.edu/labels/print?id=12345&size=small
```

**Print Small Label by Asset Name**:

```
https://rt.yourdomain.edu/labels/print?name=Chromebook-Charger-101&size=small
```

**Download PDF (for batch printing)**:

```
https://rt.yourdomain.edu/labels/print?id=12345&size=small&format=pdf
```

**Large Label (backward compatible, no size param)**:

```
https://rt.yourdomain.edu/labels/print?id=12345
```

---

## Label Layout Reference

### Small Label Dimensions: 29mm x 90.3mm (1.1" x 3.5")

```
┌─────────────────────────────────────────────┐ ← 29mm
│  ┌──────┐                                   │
│  │      │  Student Chromebook Charger...    │ ← Asset name (10pt, truncated)
│  │ QR   │                                   │
│  │ Code │                                   │
│  │      │                                   │
│  │20x20 │                                   │
│  └──────┘                                   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ |||||| ASSET-12345 |||||||||||||||| │   │ ← Barcode (70mm x 8mm)
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                90.3mm
```

**Key Differences from Large Labels**:

- **No Serial Number**: Omitted to save space (small devices often lack serials)
- **Smaller QR Code**: 20mm x 20mm (vs 50mm on large labels)
- **Compact Barcode**: 8mm tall (vs 15mm on large labels)
- **Smaller Font**: 10pt (vs 14pt on large labels)
- **Dynamic Truncation**: Asset names longer than 60mm get "..." suffix

---

## Troubleshooting

### QR Code Not Scanning

**Symptom**: Phone/scanner can't read QR code on printed label

**Solutions**:

1. **Check print quality**: Ensure thermal printer is set to high DPI (300+ recommended)
2. **Verify printer ribbon/paper**: Replace if faded or low quality
3. **Test before printing**: Use preview mode and scan QR on screen
4. **Use large label**: If asset URL is very long (>80 characters), switch to large label

**Why this happens**: Small QR codes (20mm) have limited data capacity. Very long URLs may exceed scannability threshold.

---

### Asset Name Cut Off Too Much

**Symptom**: Truncated name not identifiable (e.g., "Student..." instead of "Student Chromebook Charger...")

**Solutions**:

1. **Shorten asset name in RT**: Edit asset name to be more concise (e.g., "SCC-101" instead of "Student Chromebook Charger Room 204")
2. **Use large label**: Large labels support 90mm text width (50% more space)
3. **Check preview**: Always preview before printing to verify readability

**Why this happens**: Small labels have 60mm max text width. Names >15-20 characters may truncate.

---

### Wrong Label Size Selected

**Symptom**: System defaulted to small label for a Chromebook (or vice versa)

**Solutions**:

1. **Manual override**: Always check radio button selection before printing
2. **Update asset Type**: Verify asset Type field in RT is correct (Type drives default selection)
3. **Report bug**: If asset Type is correct but wrong default, report to IT

**Why this happens**: Default logic uses RT "Type" custom field. If Type is misconfigured (e.g., Chromebook marked as "Charger"), default will be wrong.

---

### Barcode Not Scanning

**Symptom**: Handheld scanner beeps but doesn't read barcode

**Solutions**:

1. **Check scanner settings**: Ensure Code128 barcode type enabled
2. **Verify print quality**: Barcode bars must be crisp (no smudging)
3. **Test orientation**: Scan horizontally (barcode is landscape on small labels)
4. **Clean scanner lens**: Dirt on scanner window prevents reads

**Why this happens**: Code128 barcodes at 8mm height are near minimum scannable size. Print quality must be high.

---

## PDF Export for Batch Printing

### When to Use PDF Export:

- Printing >10 labels at once (batch mode)
- Using external print services (e.g., label vendor)
- Archiving label designs for reprinting

### How to Batch Export:

**Single Asset PDF**:

```bash
# Download PDF for one asset
curl -o label-12345.pdf "https://rt.example.edu/labels/print?id=12345&size=small&format=pdf"
```

**Batch Export (via script)**:

```bash
# Export PDFs for multiple assets
for asset_id in 12345 12346 12347; do
    curl -o "label-${asset_id}.pdf" \
         "https://rt.example.edu/labels/print?id=${asset_id}&size=small&format=pdf"
done
```

**Merge PDFs (macOS)**:

```bash
# Combine multiple PDFs into one for batch printing
/System/Library/Automator/Combine\ PDF\ Pages.action/Contents/Resources/join.py \
    -o batch-labels.pdf label-*.pdf
```

---

## Printer Configuration

### Thermal Label Printers (Recommended):

- **Brother QL-820NWB** (Wi-Fi, 300 DPI)
- **Dymo LabelWriter 4XL** (USB, 300 DPI)
- **Zebra GK420d** (USB/Ethernet, 203 DPI)

### Settings for Small Labels:

1. **Paper Size**: Custom → 29mm x 90.3mm (or 1.1" x 3.5")
2. **Print Quality**: High / 300 DPI
3. **Margins**: None (borderless printing)
4. **Orientation**: Portrait (29mm width)

### Browser Print Settings:

- **Paper Size**: "Custom" → 29mm x 90.3mm
- **Margins**: None
- **Headers/Footers**: Disabled
- **Background Graphics**: Enabled (for QR/barcode images)

---

## Best Practices

### ✅ Do:

- Preview labels before printing (catch truncation/QR issues early)
- Test scan QR code and barcode after printing
- Use small labels for chargers/accessories (saves label cost)
- Keep asset names concise in RT (improves small label readability)
- Print test label before batch runs (verify printer settings)

### ❌ Don't:

- Don't use small labels for Chromebooks (serial number omitted)
- Don't override default size without reason (defaults are optimized)
- Don't ignore preview warnings (red/yellow indicators are critical)
- Don't use low-quality printers (<200 DPI) for small labels
- Don't batch print without testing one label first

---

## Quick Reference Card

| Task                      | URL                                            | Notes                   |
| ------------------------- | ---------------------------------------------- | ----------------------- |
| Print small label (by ID) | `/labels/print?id=12345&size=small`            | Auto-selects chargers   |
| Print large label (by ID) | `/labels/print?id=12345`                       | Default for Chromebooks |
| Download PDF (small)      | `/labels/print?id=12345&size=small&format=pdf` | For batch printing      |
| Print by asset name       | `/labels/print?name=Charger-101&size=small`    | Alternative to ID       |

---

## Support

### Common Issues:

- **QR not scanning**: Check print DPI, test URL length
- **Name too truncated**: Shorten asset name in RT or use large label
- **Wrong default size**: Verify asset Type field in RT
- **Barcode not scanning**: Ensure Code128 enabled on scanner

### Report Issues:

- Email: helpdesk@yourdomain.edu
- Slack: #it-support
- RT Queue: "IT Systems" → "Label Printing"

---

**Version**: 1.0 (Phase 2 Initial Release)  
**Last Updated**: 2025-01-08
