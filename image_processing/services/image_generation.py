from typing import Tuple, Dict, Any
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import base64
import time
import requests
import hashlib
import random

from .log_utils import log_ai_request, log_ai_response, log_ai_error


def _fallback_local(description: str) -> Tuple[bytes, str, Dict[str, Any]]:
    img = Image.new('RGB', (640, 360), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    text = (description or 'Generated Image')[:100]
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((20, 160), text, fill=(0, 0, 0), font=font)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue(), 'png', {"provider": "local", "duration_ms": 0}


def _request_json(url: str, headers: dict, payload: dict, provider: str) -> tuple[int, dict]:
    log_ai_request(provider, url, {k: payload.get(k) for k in ("prompt", "size", "model") if k in payload})
    t0 = time.time()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        latency = int((time.time() - t0) * 1000)
        data = {}
        try:
            data = resp.json()
        except Exception:
            pass
        if resp.ok:
            log_ai_response(provider, resp.status_code, latency, {"keys": list(data.keys())})
        else:
            log_ai_error(provider, resp.status_code, data.get("error") or resp.text[:200])
        return resp.status_code, data
    except requests.RequestException as e:
        log_ai_error(provider, None, str(e))
        return 0, {"error": str(e)}


def generate_illustration(description: str, api_key: str = '', api_base: str = '', provider: str = '') -> Tuple[bytes, str, Dict[str, Any]]:
    provider = (provider or '').lower().strip() or 'local'
    if provider == 'local' or not api_key or not api_base:
        return _fallback_local(description)

    # Normalize base URL
    base = api_base.rstrip('/')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # OpenAI-like interface
    if provider in ("openai", "groq", "grok"):
        # Note: Groq doesn't support image generation natively yet
        # For Groq, we'll use enhanced local generation with AI-powered description
        if provider in ("groq", "grok"):
            try:
                # Use Groq's vision model to enhance the description
                chat_url = f"{base}/chat/completions"
                chat_payload = {
                    "model": "llama-3.2-90b-vision-preview",
                    "messages": [{"role": "user", "content": f"Describe in vivid visual detail: {description}"}],
                    "max_tokens": 200
                }
                status2, data2 = _request_json(chat_url, headers, chat_payload, provider)
                if status2 == 200 and isinstance(data2, dict):
                    enhanced = data2.get('choices', [{}])[0].get('message', {}).get('content', description)
                    # Generate enhanced local image
                    img = Image.new('RGB', (640, 360), color=(240, 248, 255))
                    draw = ImageDraw.Draw(img)
                    try:
                        font = ImageFont.load_default()
                    except Exception:
                        font = None
                    # Wrap text nicely
                    words = (enhanced or description)[:300].split()
                    lines = []
                    current = []
                    for w in words:
                        current.append(w)
                        if len(' '.join(current)) > 45:
                            lines.append(' '.join(current[:-1]))
                            current = [w]
                    if current:
                        lines.append(' '.join(current))
                    y = 60
                    for line in lines[:8]:
                        draw.text((20, y), line, fill=(30, 30, 30), font=font)
                        y += 18
                    buf = BytesIO()
                    img.save(buf, format='PNG')
                    return buf.getvalue(), 'png', {"provider": f"{provider}_ai_enhanced", "duration_ms": 0}
            except Exception:
                pass
            return _fallback_local(description)
        
        # OpenAI DALL-E
        url = f"{base}/images/generations"
        payload = {"prompt": description, "n": 1, "size": "512x512", "response_format": "b64_json"}
        status, data = _request_json(url, headers, payload, provider)
        if status == 200 and isinstance(data, dict):
            try:
                b64 = data.get('data', [{}])[0].get('b64_json')
                if b64:
                    return base64.b64decode(b64), 'png', {"provider": provider, "duration_ms": data.get('latency_ms', 0)}
            except Exception:
                pass
        return _fallback_local(description)

    # Pollinations.ai (FREE, no API key needed!)
    if provider == 'pollinations':
        try:
            # Pollinations.ai - completely free, no auth needed
            prompt_encoded = requests.utils.quote(description)
            seed = random.randint(1, 1000000)
            url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=512&height=512&seed={seed}&nologo=true"
            log_ai_request(provider, url, {"prompt": description})
            t0 = time.time()
            resp = requests.get(url, timeout=60)
            latency = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                log_ai_response(provider, 200, latency, {"size": len(resp.content)})
                return resp.content, 'png', {"provider": provider, "duration_ms": latency}
            else:
                log_ai_error(provider, resp.status_code, resp.text[:200])
        except Exception as e:
            log_ai_error(provider, None, str(e))
        return _fallback_local(description)
    
    # Hugging Face (FREE!)
    if provider == 'huggingface':
        # Use Stable Diffusion via Hugging Face Inference API (free tier available)
        model = "stabilityai/stable-diffusion-2-1"  # or "runwayml/stable-diffusion-v1-5"
        url = f"https://api-inference.huggingface.co/models/{model}"
        hf_headers = {
            'Authorization': f'Bearer {api_key}',
        }
        t0 = time.time()
        try:
            log_ai_request(provider, url, {"prompt": description})
            resp = requests.post(url, headers=hf_headers, json={"inputs": description}, timeout=60)
            latency = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                log_ai_response(provider, 200, latency, {"size": len(resp.content)})
                return resp.content, 'png', {"provider": provider, "duration_ms": latency}
            else:
                log_ai_error(provider, resp.status_code, resp.text[:200])
        except Exception as e:
            log_ai_error(provider, None, str(e))
        return _fallback_local(description)
    
    # Stability AI
    if provider == 'stability':
        url = f"{base}/v1/generation/stable-diffusion-v1-6/text-to-image"
        status, data = _request_json(url, headers, {"text_prompts": [{"text": description}]}, provider)
        if status == 200 and isinstance(data, dict):
            try:
                artifacts = data.get('artifacts') or []
                if artifacts:
                    b64 = artifacts[0].get('base64')
                    if b64:
                        return base64.b64decode(b64), 'png', {"provider": provider, "duration_ms": 0}
            except Exception:
                pass
        return _fallback_local(description)

    # Auto mode: try multiple providers in order
    if provider == 'auto':
        # Try Pollinations first (fastest, no auth)
        try:
            prompt_encoded = requests.utils.quote(description)
            seed = random.randint(1, 1000000)
            url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=512&height=512&seed={seed}&nologo=true"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.content, 'png', {"provider": "pollinations", "duration_ms": 0}
        except Exception:
            pass
        
        # Try Hugging Face if available
        hf_key = api_key or ''
        if hf_key and hf_key.startswith('hf_'):
            try:
                model = "stabilityai/stable-diffusion-2-1"
                url = f"https://api-inference.huggingface.co/models/{model}"
                headers = {'Authorization': f'Bearer {hf_key}'}
                resp = requests.post(url, headers=headers, json={"inputs": description}, timeout=30)
                if resp.status_code == 200:
                    return resp.content, 'png', {"provider": "huggingface", "duration_ms": 0}
            except Exception:
                pass
        
        # Fallback to local
        return _fallback_local(description)
    
    # Unknown provider → local
    return _fallback_local(description)
