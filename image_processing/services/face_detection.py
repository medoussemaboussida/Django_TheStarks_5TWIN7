from typing import Dict, Tuple
import os
import base64
import requests


def _opencv_detect(path: str) -> int:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        # Read bytes to avoid Windows path/encoding problems
        with open(path, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            return 0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        cascades = [
            'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_alt2.xml',
            'haarcascade_profileface.xml',
        ]
        params = [
            (1.1, 5),
            (1.05, 5),
            (1.2, 3),
        ]
        total = 0
        for cfile in cascades:
            clf = cv2.CascadeClassifier(cv2.data.haarcascades + cfile)
            if clf.empty():
                continue
            for scale, neigh in params:
                faces = clf.detectMultiScale(gray, scaleFactor=scale, minNeighbors=neigh)
                total = max(total, len(faces))
                if total:
                    return total
        return total
    except Exception:
        return 0


def _dlib_like_detect(path: str) -> int:
    try:
        import face_recognition  # type: ignore
        image = face_recognition.load_image_file(path)
        locs = face_recognition.face_locations(image, model='hog')
        return len(locs)
    except Exception:
        return 0


def _opencv_dnn_detect(path: str) -> int:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        proto = os.getenv('FACE_DNN_PROTO', '')
        model = os.getenv('FACE_DNN_MODEL', '')
        if not (proto and model) or not (os.path.exists(proto) and os.path.exists(model)):
            return 0
        net = cv2.dnn.readNetFromCaffe(proto, model)
        with open(path, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            return 0
        (h, w) = img.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        net.setInput(blob)
        detections = net.forward()
        count = 0
        for i in range(0, detections.shape[2]):
            conf = detections[0, 0, i, 2]
            if conf > 0.6:
                count += 1
        return count
    except Exception:
        return 0


def _quality_from_count(count: int) -> str:
    if count >= 1:
        return 'good' if count <= 2 else 'medium'
    return 'none'


def _groq_vision_detect(image_path: str) -> Tuple[int, str]:
    """Use Groq Vision API to detect faces with AI - returns (count, quality)"""
    try:
        from django.conf import settings
        api_key = getattr(settings, 'GROK_API_KEY', '') or getattr(settings, 'GROQ_API_KEY', '')
        api_base = getattr(settings, 'GROK_API_BASE', '') or getattr(settings, 'GROQ_API_BASE', '')
        
        if not api_key or not api_base:
            return 0, 'none'
        
        # Read and encode image - resize for API
        from PIL import Image as PILImage
        from io import BytesIO
        
        img = PILImage.open(image_path)
        img = img.convert('RGB')
        # Resize to max 1024px to avoid API issues
        img.thumbnail((1024, 1024), PILImage.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Call Groq vision model with simpler prompt
        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "model": "llama-3.2-11b-vision-preview",  # Use smaller, more stable model
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Count human faces in this image. Reply with just a number."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }],
            "max_tokens": 10,
            "temperature": 0
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '0').strip()
            # Extract number from response
            import re
            numbers = re.findall(r'\d+', content)
            count = int(numbers[0]) if numbers else 0
            
            # Determine quality based on count
            if count >= 1:
                quality = 'good' if count <= 3 else 'medium'
            else:
                quality = 'none'
            
            return count, quality
    except Exception as e:
        # Log error for debugging
        import logging
        logging.error(f"Groq Vision error: {str(e)}")
    return 0, 'none'


def detect_faces_and_tags(image_path: str) -> Dict[str, str]:
    # Try Groq Vision AI first (most accurate)
    count, quality = _groq_vision_detect(image_path)
    
    # If Groq didn't work, fallback to traditional methods
    if count == 0 and quality == 'none':
        # Try DNN first if configured
        count = _opencv_dnn_detect(image_path)
        if count == 0:
            count = _opencv_detect(image_path)
        if count == 0:
            # fallback second pass
            count = _dlib_like_detect(image_path)
        quality = _quality_from_count(count)

    if count == 0:
        return {"contains_face": "no_face", "quality": quality, "method": "ai"}
    if count == 1:
        return {"contains_face": "contains_face", "count": 1, "quality": quality, "method": "ai"}
    return {"contains_face": "multiple_faces", "count": count, "quality": quality, "method": "ai"}
