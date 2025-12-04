"""
Label utility functions for QR codes and barcodes.
"""
import io
import base64
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from PIL import Image
from barcode import Code128
from barcode.writer import ImageWriter
import logging

logger = logging.getLogger(__name__)


def generate_qr_code(url, box_size=10):
    """
    Generate a QR code image and return as base64 string.
    
    Args:
        url (str): URL to encode in the QR code
        box_size (int): Size of each box in pixels (default: 10 for large labels, use 5 for small labels)
        
    Returns:
        str: Base64 encoded QR code image
    """
    try:
        # QR code with higher error correction for better resilience
        qr = qrcode.QRCode(
            version=1,  # Fixed version to avoid issues
            error_correction=ERROR_CORRECT_M,  # Medium error correction (15% damage recovery)
            box_size=box_size,  # Configurable box size for different label sizes
            border=1      # Minimum quiet zone (1 module)
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Generate image directly to buffer
        qr_buffer = io.BytesIO()
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_buffer)
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode("utf-8")
        qr_buffer.close()
        return qr_base64
    except Exception as e:
        logger.error(f"QR code generation failed: {e}")
        # Create a simple fallback QR code with plain PIL
        try:
            # Generate a simple black square as fallback
            size = 200
            fallback = Image.new('RGB', (size, size), color='white')
            # Add a border to make it look like a QR code
            for i in range(10):
                for j in range(10):
                    if (i == 0 or j == 0 or i == 9 or j == 9) or (i in [2,7] and j in [2,7]):
                        # Draw black squares in QR pattern
                        x, y = i*20, j*20
                        block = Image.new('RGB', (20, 20), color='black')
                        fallback.paste(block, (x, y))
            fallback_buffer = io.BytesIO()
            fallback.save(fallback_buffer)
            fallback_base64 = base64.b64encode(fallback_buffer.getvalue()).decode("utf-8")
            fallback_buffer.close()
            return fallback_base64
        except Exception as fallback_error:
            logger.error(f"QR code fallback failed: {fallback_error}")
            # If all else fails, return an empty string
            return ""


def calculate_checksum(content):
    """
    Calculate a simple verification checksum for barcode data.
    
    Args:
        content (str): The content to calculate checksum for
        
    Returns:
        str: The original content followed by a verification digit
    """
    # Simple checksum algorithm - sum ASCII values and take modulo 10
    checksum = sum(ord(c) for c in content) % 10
    return f"{content}*{checksum}"


def generate_barcode(content, width_mm=80.0, height_mm=15.0):
    """
    Generate a barcode image and return as base64 string.
    Appends a verification checksum to the content for error detection.
    
    Args:
        content (str): Content to encode in the barcode
        width_mm (float): Target barcode width in millimeters (default: 80.0 for large labels)
        height_mm (float): Target barcode height in millimeters (default: 15.0 for large labels)
        
    Returns:
        str: Base64 encoded barcode image
    """
    # Add verification checksum to content
    verified_content = calculate_checksum(content)
    barcode = Code128(verified_content, writer=ImageWriter())
    
    # Adjust barcode parameters for better printing with configurable dimensions
    # Using module_height to control the height (in mm)
    barcode_writer_options = {
        "module_width": 0.2,  # Thin bars for better density
        "module_height": height_mm,  # Configurable height in mm
        "quiet_zone": 2.5,  # Standard quiet zone
        "write_text": False,
        "font_size": 8,
        "text_distance": 1.0,
        "dpi": 300  # Higher DPI for better print quality
    }
    barcode_buffer = io.BytesIO()
    barcode.write(barcode_buffer, options=barcode_writer_options)
    
    # Resize the barcode to match target width while maintaining quality
    try:
        barcode_buffer.seek(0)  # Reset buffer position
        barcode_image = Image.open(barcode_buffer)
        current_width, current_height = barcode_image.size
        
        # Calculate target width in pixels (assuming 300 DPI)
        # 1 inch = 25.4mm, so pixels = (mm / 25.4) * dpi
        target_width_px = int((width_mm / 25.4) * 300)
        
        # Maintain aspect ratio for height or use target height
        # Scale height proportionally to width change
        scale_factor = target_width_px / current_width
        target_height_px = int(current_height * scale_factor)
        
        # Use LANCZOS for best quality resizing
        try:
            resize_method = Image.Resampling.LANCZOS
        except AttributeError:
            resize_method = 1  # LANCZOS constant for older PIL versions
            
        resized_barcode = barcode_image.resize((target_width_px, target_height_px), resize_method)
        
        # Save the resized image with high quality settings
        resized_buffer = io.BytesIO()
        resized_barcode.save(
            resized_buffer, 
            format="PNG", 
            optimize=True, 
            compress_level=1  # Lower compression for better quality
        )
        barcode_base64 = base64.b64encode(resized_buffer.getvalue()).decode("utf-8")
        
        # Close buffers
        resized_buffer.close()
    except Exception as img_error:
        logger.error(f"Error processing barcode image: {img_error}")
        # Fall back to original barcode if resize fails
        barcode_buffer.seek(0)  # Reset buffer position
        barcode_base64 = base64.b64encode(barcode_buffer.getvalue()).decode("utf-8")
        
    # Close buffer
    barcode_buffer.close()
    return barcode_base64


def get_custom_field_value(custom_fields, field_name, default="N/A"):
    """
    Extract a value from the custom fields array by field name.
    
    Args:
        custom_fields (list): List of custom field dictionaries
        field_name (str): Name of the field to extract
        default (str): Default value if field not found
        
    Returns:
        str: The value of the field or default if not found
    """
    return next(
        (field.get("values", [None])[0] 
         for field in custom_fields 
         if field.get("name") == field_name and field.get("values")),
        default
    )


def get_default_label_size(asset_type: str, small_label_types=None) -> str:
    """
    Determine default label size based on asset type.
    
    Args:
        asset_type: The type of asset (e.g., 'Charger', 'Laptop', 'Cable')
        small_label_types: List of asset types that should use small labels
        
    Returns:
        'small' for chargers and similar small items, 'large' for everything else
    """
    if small_label_types is None:
        small_label_types = ['Charger', 'Power Adapter', 'Cable']
    
    # Case-insensitive comparison
    return 'small' if asset_type.lower() in [t.lower() for t in small_label_types] else 'large'
