"""
Image filtering and editing services using PIL and OpenCV
"""
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import io
import logging

logger = logging.getLogger(__name__)


def adjust_brightness(image_path: str, factor: float) -> bytes:
    """
    Adjust image brightness
    Args:
        image_path: Path to the image file
        factor: Brightness factor (0.0 = black, 1.0 = original, 2.0 = twice as bright)
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        enhancer = ImageEnhance.Brightness(img)
        result = enhancer.enhance(factor)
        
        # Convert to bytes
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Brightness adjustment failed: {str(e)}")
        raise


def adjust_contrast(image_path: str, factor: float) -> bytes:
    """
    Adjust image contrast
    Args:
        image_path: Path to the image file
        factor: Contrast factor (0.0 = gray, 1.0 = original, 2.0 = high contrast)
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        enhancer = ImageEnhance.Contrast(img)
        result = enhancer.enhance(factor)
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Contrast adjustment failed: {str(e)}")
        raise


def adjust_saturation(image_path: str, factor: float) -> bytes:
    """
    Adjust image saturation (color intensity)
    Args:
        image_path: Path to the image file
        factor: Saturation factor (0.0 = grayscale, 1.0 = original, 2.0 = very saturated)
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        enhancer = ImageEnhance.Color(img)
        result = enhancer.enhance(factor)
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Saturation adjustment failed: {str(e)}")
        raise


def adjust_sharpness(image_path: str, factor: float) -> bytes:
    """
    Adjust image sharpness
    Args:
        image_path: Path to the image file
        factor: Sharpness factor (0.0 = blurred, 1.0 = original, 2.0 = sharp)
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        enhancer = ImageEnhance.Sharpness(img)
        result = enhancer.enhance(factor)
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Sharpness adjustment failed: {str(e)}")
        raise


def apply_blur(image_path: str, radius: int = 5) -> bytes:
    """
    Apply Gaussian blur to image
    Args:
        image_path: Path to the image file
        radius: Blur radius (higher = more blur)
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        result = img.filter(ImageFilter.GaussianBlur(radius=radius))
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Blur failed: {str(e)}")
        raise


def apply_sharpen(image_path: str) -> bytes:
    """
    Apply sharpening filter
    Args:
        image_path: Path to the image file
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        result = img.filter(ImageFilter.SHARPEN)
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Sharpen failed: {str(e)}")
        raise


def apply_edge_enhance(image_path: str) -> bytes:
    """
    Enhance edges in image
    Args:
        image_path: Path to the image file
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        result = img.filter(ImageFilter.EDGE_ENHANCE)
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Edge enhance failed: {str(e)}")
        raise


def convert_to_grayscale(image_path: str) -> bytes:
    """
    Convert image to grayscale
    Args:
        image_path: Path to the image file
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        result = img.convert('L')
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Grayscale conversion failed: {str(e)}")
        raise


def apply_sepia(image_path: str) -> bytes:
    """
    Apply sepia tone filter
    Args:
        image_path: Path to the image file
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path).convert('RGB')
        width, height = img.size
        pixels = img.load()
        
        for py in range(height):
            for px in range(width):
                r, g, b = pixels[px, py]
                
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                
                pixels[px, py] = (min(tr, 255), min(tg, 255), min(tb, 255))
        
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Sepia filter failed: {str(e)}")
        raise


def rotate_image(image_path: str, angle: int) -> bytes:
    """
    Rotate image by specified angle
    Args:
        image_path: Path to the image file
        angle: Rotation angle in degrees (positive = counter-clockwise)
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        result = img.rotate(angle, expand=True, fillcolor='white')
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Rotation failed: {str(e)}")
        raise


def flip_image(image_path: str, direction: str = 'horizontal') -> bytes:
    """
    Flip image horizontally or vertically
    Args:
        image_path: Path to the image file
        direction: 'horizontal' or 'vertical'
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        
        if direction == 'horizontal':
            result = img.transpose(Image.FLIP_LEFT_RIGHT)
        elif direction == 'vertical':
            result = img.transpose(Image.FLIP_TOP_BOTTOM)
        else:
            raise ValueError("Direction must be 'horizontal' or 'vertical'")
        
        output = io.BytesIO()
        result.save(output, format=img.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Flip failed: {str(e)}")
        raise


def apply_auto_enhance(image_path: str) -> bytes:
    """
    Apply automatic enhancement (brightness, contrast, color)
    Args:
        image_path: Path to the image file
    Returns:
        Image bytes
    """
    try:
        img = Image.open(image_path)
        
        # Auto brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        
        # Auto contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        # Auto color
        enhancer = ImageEnhance.Color(img)
        result = enhancer.enhance(1.1)
        
        output = io.BytesIO()
        result.save(output, format='PNG')
        return output.getvalue()
    except Exception as e:
        logger.error(f"Auto enhance failed: {str(e)}")
        raise


# OpenCV-based filters
def apply_cartoon_effect(image_path: str) -> bytes:
    """
    Apply cartoon effect using OpenCV
    Args:
        image_path: Path to the image file
    Returns:
        Image bytes
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply median blur
        gray = cv2.medianBlur(gray, 5)
        
        # Detect edges
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                       cv2.THRESH_BINARY, 9, 9)
        
        # Apply bilateral filter for smoothing
        color = cv2.bilateralFilter(img, 9, 300, 300)
        
        # Combine edges and color
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        
        # Convert to bytes
        _, buffer = cv2.imencode('.png', cartoon)
        return buffer.tobytes()
    except Exception as e:
        logger.error(f"Cartoon effect failed: {str(e)}")
        raise


def apply_sketch_effect(image_path: str) -> bytes:
    """
    Apply pencil sketch effect using OpenCV
    Args:
        image_path: Path to the image file
    Returns:
        Image bytes
    """
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Invert the grayscale image
        inv_gray = 255 - gray
        
        # Apply Gaussian blur
        blur = cv2.GaussianBlur(inv_gray, (21, 21), 0)
        
        # Invert the blurred image
        inv_blur = 255 - blur
        
        # Create sketch
        sketch = cv2.divide(gray, inv_blur, scale=256.0)
        
        _, buffer = cv2.imencode('.png', sketch)
        return buffer.tobytes()
    except Exception as e:
        logger.error(f"Sketch effect failed: {str(e)}")
        raise
