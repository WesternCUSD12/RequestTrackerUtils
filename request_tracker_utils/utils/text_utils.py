"""Text manipulation utilities for label generation.

This module provides text truncation and formatting utilities for generating
labels with constrained dimensions.
"""

from reportlab.pdfbase import pdfmetrics


def truncate_text_to_width(
    text: str,
    font_name: str,
    font_size: int,
    max_width_mm: float
) -> str:
    """Truncate text to fit within a specified width using binary search.
    
    Uses ReportLab's pdfmetrics.stringWidth() for accurate text measurement
    in the given font and size. If the text exceeds max_width_mm, it is
    truncated with an ellipsis ("...") suffix.
    
    Args:
        text: Input string to truncate
        font_name: ReportLab font name (e.g., 'Helvetica', 'Times-Roman')
        font_size: Font size in points
        max_width_mm: Maximum allowed width in millimeters
        
    Returns:
        Original text if it fits, truncated text + "..." if too long,
        or empty string if input is empty
        
    Examples:
        >>> truncate_text_to_width("Hello World", "Helvetica", 12, 20.0)
        "Hello..."
        >>> truncate_text_to_width("Hi", "Helvetica", 12, 50.0)
        "Hi"
        >>> truncate_text_to_width("", "Helvetica", 12, 20.0)
        ""
    """
    # Handle edge cases
    if not text:
        return ""
    
    # Convert mm to points (1mm = 2.834645 points)
    max_width_pt = max_width_mm * 2.834645
    
    # Measure full text width
    full_width = pdfmetrics.stringWidth(text, font_name, font_size)
    
    # If text fits, return as-is
    if full_width <= max_width_pt:
        return text
    
    # Measure ellipsis width
    ellipsis = "..."
    ellipsis_width = pdfmetrics.stringWidth(ellipsis, font_name, font_size)
    
    # If a single character is too wide, return just ellipsis
    single_char_width = pdfmetrics.stringWidth(text[0], font_name, font_size)
    if single_char_width + ellipsis_width > max_width_pt:
        return ellipsis
    
    # Binary search for maximum character count that fits with ellipsis
    left = 1
    right = len(text)
    best_length = 0
    
    while left <= right:
        mid = (left + right) // 2
        truncated = text[:mid] + ellipsis
        truncated_width = pdfmetrics.stringWidth(truncated, font_name, font_size)
        
        if truncated_width <= max_width_pt:
            best_length = mid
            left = mid + 1
        else:
            right = mid - 1
    
    # If we couldn't fit any characters with ellipsis, return just ellipsis
    if best_length == 0:
        return ellipsis
    
    return text[:best_length] + ellipsis
