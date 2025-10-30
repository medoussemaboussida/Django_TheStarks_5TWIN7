"""
Advanced AI image analysis using Groq Vision API
"""
import requests
import base64
import logging
from django.conf import settings
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io

logger = logging.getLogger(__name__)


def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64 for API"""
    try:
        # Open and potentially resize image if too large
        from PIL import Image
        import io
        
        img = Image.open(image_path)
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Resize if image is too large (max 2048px)
        max_size = 2048
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Image encoding error: {str(e)}")
        # Fallback to direct encoding
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')


def analyze_image_with_vision(image_path: str, prompt: str) -> dict:
    """
    Analyze image using Groq Vision API
    Returns: {'success': bool, 'result': str, 'error': str}
    """
    try:
        groq_key = getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'GROK_API_KEY', '')
        groq_base = getattr(settings, 'GROQ_API_BASE', '') or getattr(settings, 'GROK_API_BASE', '')
        
        if not groq_key or not groq_base:
            return {'success': False, 'result': '', 'error': 'Groq API not configured'}
        
        # Encode image
        image_base64 = encode_image_to_base64(image_path)
        
        url = f"{groq_base.rstrip('/')}/chat/completions"
        headers = {
            'Authorization': f'Bearer {groq_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"Vision analysis successful: {len(content)} chars")
            return {'success': True, 'result': content, 'error': ''}
        else:
            error_msg = f"API error: {response.status_code}"
            logger.error(f"Vision analysis failed: {error_msg}")
            return {'success': False, 'result': '', 'error': error_msg}
            
    except Exception as e:
        logger.error(f"Vision analysis exception: {str(e)}")
        return {'success': False, 'result': '', 'error': str(e)}


def detect_objects_and_people(image_path: str) -> dict:
    """
    Detect objects, people, and animals in image
    Returns: {'success': bool, 'objects': list, 'people_count': int, 'description': str}
    """
    prompt = """Analyze this image and provide:
1. List all objects you can see (comma-separated)
2. Count of people in the image
3. Count of animals (specify type)
4. Brief description of the scene

Format your response as:
Objects: [list]
People: [number]
Animals: [type and number]
Scene: [description]"""
    
    result = analyze_image_with_vision(image_path, prompt)
    
    if result['success']:
        content = result['result']
        # Parse response
        objects = []
        people_count = 0
        animals = []
        description = content
        
        # Simple parsing
        for line in content.split('\n'):
            if line.startswith('Objects:'):
                objects = [obj.strip() for obj in line.replace('Objects:', '').split(',')]
            elif line.startswith('People:'):
                try:
                    people_count = int(''.join(filter(str.isdigit, line)))
                except:
                    people_count = 0
            elif line.startswith('Animals:'):
                animals.append(line.replace('Animals:', '').strip())
        
        return {
            'success': True,
            'objects': objects,
            'people_count': people_count,
            'animals': animals,
            'description': content,
            'error': ''
        }
    else:
        return {
            'success': False,
            'objects': [],
            'people_count': 0,
            'animals': [],
            'description': '',
            'error': result['error']
        }


def detect_emotions(image_path: str) -> dict:
    """
    Detect emotions from faces in image
    Returns: {'success': bool, 'emotions': list, 'dominant_emotion': str}
    """
    prompt = """Analyze the emotions of people in this image. 
For each person visible, identify their emotion (happy, sad, neutral, surprised, angry, fearful, disgusted).
Also identify the overall mood of the image.

Format: 
Person 1: [emotion]
Person 2: [emotion]
Overall mood: [description]"""
    
    result = analyze_image_with_vision(image_path, prompt)
    
    if result['success']:
        emotions = []
        dominant = 'neutral'
        
        for line in result['result'].split('\n'):
            if 'Person' in line and ':' in line:
                emotion = line.split(':')[1].strip().lower()
                emotions.append(emotion)
            elif 'Overall mood' in line:
                dominant = line.split(':')[1].strip()
        
        return {
            'success': True,
            'emotions': emotions,
            'dominant_emotion': dominant,
            'description': result['result'],
            'error': ''
        }
    else:
        return {
            'success': False,
            'emotions': [],
            'dominant_emotion': 'unknown',
            'description': '',
            'error': result['error']
        }


def recognize_scene(image_path: str) -> dict:
    """
    Recognize scene type and generate auto-tags
    Returns: {'success': bool, 'scene_type': str, 'tags': list, 'location': str}
    """
    prompt = """Analyze this image and identify:
1. Scene type (indoor/outdoor, beach, office, home, party, nature, city, etc.)
2. Time of day (morning, afternoon, evening, night)
3. Weather (if outdoor)
4. Activity happening
5. Suggest 5-10 relevant tags for this image

Format:
Scene: [type]
Time: [time of day]
Weather: [weather]
Activity: [activity]
Tags: [tag1, tag2, tag3, ...]"""
    
    result = analyze_image_with_vision(image_path, prompt)
    
    if result['success']:
        scene_type = 'unknown'
        tags = []
        time_of_day = ''
        weather = ''
        activity = ''
        
        for line in result['result'].split('\n'):
            if line.startswith('Scene:'):
                scene_type = line.replace('Scene:', '').strip()
            elif line.startswith('Tags:'):
                tags_str = line.replace('Tags:', '').strip()
                tags = [tag.strip() for tag in tags_str.split(',')]
            elif line.startswith('Time:'):
                time_of_day = line.replace('Time:', '').strip()
            elif line.startswith('Weather:'):
                weather = line.replace('Weather:', '').strip()
            elif line.startswith('Activity:'):
                activity = line.replace('Activity:', '').strip()
        
        return {
            'success': True,
            'scene_type': scene_type,
            'tags': tags,
            'time_of_day': time_of_day,
            'weather': weather,
            'activity': activity,
            'description': result['result'],
            'error': ''
        }
    else:
        return {
            'success': False,
            'scene_type': 'unknown',
            'tags': [],
            'time_of_day': '',
            'weather': '',
            'activity': '',
            'description': '',
            'error': result['error']
        }


def extract_text_ocr(image_path: str) -> dict:
    """
    Extract text from image using Groq Vision (OCR)
    Returns: {'success': bool, 'text': str, 'has_text': bool}
    """
    prompt = """Extract ALL text visible in this image. 
Include handwritten text, printed text, signs, labels, etc.
If there is no text, respond with "No text found".

Extracted text:"""
    
    result = analyze_image_with_vision(image_path, prompt)
    
    if result['success']:
        text = result['result'].replace('Extracted text:', '').strip()
        has_text = text.lower() != 'no text found' and len(text) > 0
        
        return {
            'success': True,
            'text': text,
            'has_text': has_text,
            'error': ''
        }
    else:
        return {
            'success': False,
            'text': '',
            'has_text': False,
            'error': result['error']
        }


def generate_caption(image_path: str) -> dict:
    """
    Generate automatic caption for image
    Returns: {'success': bool, 'caption': str, 'detailed_caption': str}
    """
    prompt = """Generate two captions for this image:
1. A short caption (one sentence, 10-15 words)
2. A detailed caption (2-3 sentences describing the scene, mood, and context)

Format:
Short: [caption]
Detailed: [caption]"""
    
    result = analyze_image_with_vision(image_path, prompt)
    
    if result['success']:
        short_caption = ''
        detailed_caption = ''
        
        for line in result['result'].split('\n'):
            if line.startswith('Short:'):
                short_caption = line.replace('Short:', '').strip()
            elif line.startswith('Detailed:'):
                detailed_caption = line.replace('Detailed:', '').strip()
        
        return {
            'success': True,
            'caption': short_caption or result['result'][:100],
            'detailed_caption': detailed_caption or result['result'],
            'error': ''
        }
    else:
        return {
            'success': False,
            'caption': '',
            'detailed_caption': '',
            'error': result['error']
        }


def extract_exif_metadata(image_path: str) -> dict:
    """
    Extract EXIF metadata including GPS location
    Returns: {'success': bool, 'metadata': dict, 'gps': dict}
    """
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        
        if not exif_data:
            return {
                'success': True,
                'metadata': {},
                'gps': {},
                'has_gps': False,
                'error': ''
            }
        
        metadata = {}
        gps_info = {}
        
        # Extract standard EXIF
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            
            if tag == 'GPSInfo':
                # Extract GPS data
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = gps_value
            else:
                # Convert to string if not serializable
                try:
                    metadata[tag] = str(value) if not isinstance(value, (str, int, float, bool)) else value
                except:
                    pass
        
        # Parse GPS coordinates
        has_gps = False
        latitude = None
        longitude = None
        
        if gps_info:
            try:
                if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                    lat = gps_info['GPSLatitude']
                    lon = gps_info['GPSLongitude']
                    lat_ref = gps_info.get('GPSLatitudeRef', 'N')
                    lon_ref = gps_info.get('GPSLongitudeRef', 'E')
                    
                    # Convert to decimal degrees
                    latitude = lat[0] + lat[1]/60 + lat[2]/3600
                    if lat_ref == 'S':
                        latitude = -latitude
                    
                    longitude = lon[0] + lon[1]/60 + lon[2]/3600
                    if lon_ref == 'W':
                        longitude = -longitude
                    
                    gps_info['latitude'] = latitude
                    gps_info['longitude'] = longitude
                    has_gps = True
            except Exception as e:
                logger.warning(f"GPS parsing error: {str(e)}")
        
        return {
            'success': True,
            'metadata': metadata,
            'gps': gps_info,
            'has_gps': has_gps,
            'latitude': latitude,
            'longitude': longitude,
            'error': ''
        }
        
    except Exception as e:
        logger.error(f"EXIF extraction error: {str(e)}")
        return {
            'success': False,
            'metadata': {},
            'gps': {},
            'has_gps': False,
            'error': str(e)
        }


def comprehensive_analysis(image_path: str) -> dict:
    """
    Perform comprehensive AI analysis on image
    Combines all analysis functions
    """
    results = {
        'objects': detect_objects_and_people(image_path),
        'emotions': detect_emotions(image_path),
        'scene': recognize_scene(image_path),
        'ocr': extract_text_ocr(image_path),
        'caption': generate_caption(image_path),
        'exif': extract_exif_metadata(image_path)
    }
    
    # Create summary
    summary = {
        'has_people': results['objects'].get('people_count', 0) > 0,
        'has_text': results['ocr'].get('has_text', False),
        'has_gps': results['exif'].get('has_gps', False),
        'scene_type': results['scene'].get('scene_type', 'unknown'),
        'dominant_emotion': results['emotions'].get('dominant_emotion', 'neutral'),
        'suggested_tags': results['scene'].get('tags', []),
        'caption': results['caption'].get('caption', ''),
        'location': None
    }
    
    if results['exif'].get('has_gps'):
        summary['location'] = {
            'latitude': results['exif'].get('latitude'),
            'longitude': results['exif'].get('longitude')
        }
    
    return {
        'success': True,
        'analysis': results,
        'summary': summary
    }
