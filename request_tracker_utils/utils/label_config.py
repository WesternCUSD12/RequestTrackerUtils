"""Label template configuration module.

This module defines the LabelTemplate dataclass and provides configurations
for different label sizes (large and small).
"""

from dataclasses import dataclass


@dataclass
class LabelTemplate:
    """Configuration for a label template with dimensions and formatting options.
    
    Attributes:
        name: Template identifier ('large' or 'small')
        width_mm: Label width in millimeters
        height_mm: Label height in millimeters
        qr_size_mm: QR code size in millimeters (square)
        barcode_width_mm: Barcode width in millimeters
        barcode_height_mm: Barcode height in millimeters
        font_size_pt: Base font size in points
        show_serial: Whether to display serial number on the label
        text_max_width_mm: Maximum width for text fields in millimeters
    """
    name: str
    width_mm: float
    height_mm: float
    qr_size_mm: float
    barcode_width_mm: float
    barcode_height_mm: float
    font_size_pt: int
    show_serial: bool
    text_max_width_mm: float
    
    def __post_init__(self):
        """Validate template dimensions."""
        if self.width_mm <= 0 or self.height_mm <= 0:
            raise ValueError(f"Label dimensions must be positive: {self.width_mm}x{self.height_mm}mm")
        if self.qr_size_mm <= 0:
            raise ValueError(f"QR code size must be positive: {self.qr_size_mm}mm")
        if self.barcode_width_mm <= 0 or self.barcode_height_mm <= 0:
            raise ValueError(f"Barcode dimensions must be positive: {self.barcode_width_mm}x{self.barcode_height_mm}mm")
        if self.font_size_pt < 6:
            raise ValueError(f"Font size must be at least 6pt: {self.font_size_pt}pt")
        if self.text_max_width_mm <= 0 or self.text_max_width_mm >= self.width_mm:
            raise ValueError(f"Text max width must be positive and less than label width: {self.text_max_width_mm}mm < {self.width_mm}mm")


LABEL_TEMPLATES = {
    'large': LabelTemplate(
        name='large',
        width_mm=100.0,
        height_mm=62.0,
        qr_size_mm=50.0,
        barcode_width_mm=80.0,
        barcode_height_mm=15.0,
        font_size_pt=14,
        show_serial=True,
        text_max_width_mm=90.0
    ),
    'small': LabelTemplate(
        name='small',
        width_mm=90.3,  # Landscape: width is the longer dimension
        height_mm=29.0,  # Landscape: height is the shorter dimension
        qr_size_mm=20.0,
        barcode_width_mm=86.0,  # Full width barcode along bottom
        barcode_height_mm=6.0,  # Reduced height to avoid overlap
        font_size_pt=11,
        show_serial=False,
        text_max_width_mm=60.0  # Max width for text in center area
    )
}
