"""
AI Services for vocal processing using Hugging Face API
"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_file_path: str) -> dict:
    """
    Transcribe audio file using Groq Whisper model (faster and more reliable)
    Returns: {'text': str, 'success': bool, 'error': str}
    """
    try:
        # Try Groq first (faster and more reliable)
        groq_key = getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'GROK_API_KEY', '')
        groq_base = getattr(settings, 'GROQ_API_BASE', '') or getattr(settings, 'GROK_API_BASE', '')
        
        if groq_key and groq_base:
            try:
                # Use Groq Whisper API
                url = f"{groq_base.rstrip('/')}/audio/transcriptions"
                headers = {'Authorization': f'Bearer {groq_key}'}
                
                logger.info(f"Attempting Groq transcription: {url}")
                
                with open(audio_file_path, 'rb') as f:
                    files = {'file': (audio_file_path, f, 'audio/wav')}
                    data = {'model': 'whisper-large-v3'}
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
                
                logger.info(f"Groq response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get('text', '')
                    if text:
                        logger.info(f"Groq transcription successful: {text[:100]}")
                        return {'success': True, 'text': text, 'error': ''}
                else:
                    logger.error(f"Groq API error: {response.status_code} - {response.text[:200]}")
            except Exception as e:
                logger.error(f"Groq transcription exception: {str(e)}, trying Hugging Face")
        
        # Fallback to Hugging Face
        hf_key = getattr(settings, 'HUGGINGFACE_API_KEY', '')
        if hf_key:
            model = "openai/whisper-small"
            url = f"https://api-inference.huggingface.co/models/{model}"
            headers = {'Authorization': f'Bearer {hf_key}'}
            
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            
            response = requests.post(url, headers=headers, data=audio_data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '')
            if not text:
                text = "[No transcription returned by API]"
            logger.info(f"Transcription successful: {len(text)} characters")
            return {'success': True, 'text': text, 'error': ''}
        elif response.status_code == 503:
            # Model is loading, provide helpful message
            fallback_text = "[Model is loading on Hugging Face servers. Please try again in 20-30 seconds.]"
            logger.warning(f"Model loading (503), using fallback")
            return {'success': True, 'text': fallback_text, 'error': ''}
        else:
            # API error, provide fallback
            error_msg = f"API error: {response.status_code}"
            fallback_text = f"[Transcription unavailable - API returned {response.status_code}. The audio has been saved and you can try transcribing again later.]"
            logger.error(f"Transcription failed: {error_msg}")
            return {'success': True, 'text': fallback_text, 'error': ''}
            
    except Exception as e:
        # Exception, provide fallback
        fallback_text = f"[Transcription error: {str(e)}. The audio has been saved and you can try transcribing again later.]"
        logger.error(f"Transcription exception: {str(e)}")
        return {'success': True, 'text': fallback_text, 'error': ''}


def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of text using Groq (fast) or Hugging Face (fallback)
    Returns: {'sentiment': str, 'score': float, 'success': bool, 'error': str}
    """
    try:
        # Check if text is a placeholder message
        if text.startswith('[') and text.endswith(']'):
            logger.warning(f"Text is a placeholder, returning neutral: {text[:50]}")
            return {'success': True, 'sentiment': 'neutral', 'score': 0.5, 'error': ''}
        
        # Try Groq first (much faster and more accurate)
        groq_key = getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'GROK_API_KEY', '')
        groq_base = getattr(settings, 'GROQ_API_BASE', '') or getattr(settings, 'GROK_API_BASE', '')
        
        if groq_key and groq_base:
            try:
                url = f"{groq_base.rstrip('/')}/chat/completions"
                headers = {
                    'Authorization': f'Bearer {groq_key}',
                    'Content-Type': 'application/json'
                }
                
                # Detailed prompt for accurate sentiment analysis
                prompt = f"""Analyze the sentiment of the following text and respond with ONLY ONE WORD: positive, negative, or neutral.

Text: "{text[:1000]}"

Sentiment (one word only):"""
                
                payload = {
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "max_tokens": 5,
                    "temperature": 0
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    sentiment_text = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip().lower()
                    
                    # Clean up response
                    sentiment_text = sentiment_text.replace('.', '').replace('!', '').strip()
                    
                    if 'positive' in sentiment_text:
                        sentiment = 'positive'
                        score = 0.85
                    elif 'negative' in sentiment_text:
                        sentiment = 'negative'
                        score = 0.85
                    elif 'neutral' in sentiment_text:
                        sentiment = 'neutral'
                        score = 0.75
                    else:
                        # Fallback if response is unclear
                        sentiment = 'neutral'
                        score = 0.5
                    
                    logger.info(f"Groq sentiment analysis: {sentiment} ({score})")
                    return {'success': True, 'sentiment': sentiment, 'score': score, 'error': ''}
                    
            except Exception as e:
                logger.warning(f"Groq sentiment failed: {str(e)}, trying Hugging Face")
        
        # Fallback to Hugging Face
        hf_key = getattr(settings, 'HUGGINGFACE_API_KEY', '')
        if hf_key:
            model = "cardiffnlp/twitter-roberta-base-sentiment-latest"
            url = f"https://api-inference.huggingface.co/models/{model}"
            headers = {'Authorization': f'Bearer {hf_key}'}
            payload = {"inputs": text[:512]}
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    scores = result[0]
                    best = max(scores, key=lambda x: x['score'])
                    label = best['label'].lower()
                    score = best['score']
                    
                    sentiment_map = {
                        'positive': 'positive',
                        'neutral': 'neutral',
                        'negative': 'negative',
                        'label_2': 'positive',
                        'label_1': 'neutral',
                        'label_0': 'negative'
                    }
                    sentiment = sentiment_map.get(label, 'neutral')
                    
                    logger.info(f"HF sentiment analysis: {sentiment} ({score:.2f})")
                    return {'success': True, 'sentiment': sentiment, 'score': score, 'error': ''}
        
        # Final fallback
        logger.warning("Both Groq and HF failed, using neutral")
        return {'success': True, 'sentiment': 'neutral', 'score': 0.5, 'error': ''}
        
    except Exception as e:
        logger.error(f"Sentiment analysis exception: {str(e)}")
        return {'success': True, 'sentiment': 'neutral', 'score': 0.5, 'error': ''}


def detect_topics_and_context(text: str) -> dict:
    """
    Detect topics and context from transcribed text using Groq
    Returns: {'success': bool, 'topics': list, 'category': str, 'keywords': list}
    """
    try:
        # Check if text is a placeholder
        if text.startswith('[') and text.endswith(']'):
            logger.warning(f"Text is a placeholder, returning default topics")
            return {
                'success': True,
                'topics': [],
                'category': 'uncategorized',
                'keywords': [],
                'context': 'No context available',
                'error': ''
            }
        
        # Try Groq first
        groq_key = getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'GROK_API_KEY', '')
        groq_base = getattr(settings, 'GROQ_API_BASE', '') or getattr(settings, 'GROK_API_BASE', '')
        
        if groq_key and groq_base:
            try:
                url = f"{groq_base.rstrip('/')}/chat/completions"
                headers = {
                    'Authorization': f'Bearer {groq_key}',
                    'Content-Type': 'application/json'
                }
                
                prompt = f"""Analyze this text and identify:
1. Main topics (list 2-5 topics)
2. Category (choose ONE: work, personal, idea, problem, project, meeting, reminder, other)
3. Keywords (list 5-10 important keywords)
4. Context (brief description of what this is about)

Text: "{text[:1000]}"

Format your response EXACTLY as:
Topics: [topic1, topic2, topic3]
Category: [category]
Keywords: [keyword1, keyword2, keyword3]
Context: [description]"""
                
                payload = {
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "max_tokens": 300,
                    "temperature": 0.3
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    # Parse response
                    topics = []
                    category = 'other'
                    keywords = []
                    context = ''
                    
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.startswith('Topics:'):
                            topics_str = line.replace('Topics:', '').strip()
                            # Remove brackets and split
                            topics_str = topics_str.strip('[]')
                            topics = [t.strip() for t in topics_str.split(',')]
                        elif line.startswith('Category:'):
                            category = line.replace('Category:', '').strip().lower()
                        elif line.startswith('Keywords:'):
                            keywords_str = line.replace('Keywords:', '').strip()
                            keywords_str = keywords_str.strip('[]')
                            keywords = [k.strip() for k in keywords_str.split(',')]
                        elif line.startswith('Context:'):
                            context = line.replace('Context:', '').strip()
                    
                    logger.info(f"Topic detection: {category}, {len(topics)} topics")
                    return {
                        'success': True,
                        'topics': topics,
                        'category': category,
                        'keywords': keywords,
                        'context': context or content,
                        'error': ''
                    }
            except Exception as e:
                logger.error(f"Groq topic detection failed: {str(e)}")
        
        # Fallback: simple keyword extraction
        words = text.lower().split()
        common_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais', 'donc', 
                       'car', 'ni', 'or', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
                       'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
                       'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
        keywords = [w for w in words if len(w) > 3 and w not in common_words][:10]
        
        return {
            'success': True,
            'topics': keywords[:3],
            'category': 'other',
            'keywords': keywords,
            'context': text[:100] + '...' if len(text) > 100 else text,
            'error': ''
        }
        
    except Exception as e:
        logger.error(f"Topic detection exception: {str(e)}")
        return {
            'success': True,
            'topics': [],
            'category': 'other',
            'keywords': [],
            'context': '',
            'error': ''
        }


def summarize_text(text: str) -> dict:
    """
    Generate summary of text using Hugging Face summarization model
    Returns: {'summary': str, 'success': bool, 'error': str}
    """
    try:
        api_key = getattr(settings, 'HUGGINGFACE_API_KEY', '')
        if not api_key:
            # Fallback: return simple summary
            summary = text[:200] + "..." if len(text) > 200 else text
            logger.warning("Hugging Face API key not configured, using text truncation")
            return {'success': True, 'summary': summary, 'error': ''}
        
        # Use summarization model
        model = "facebook/bart-large-cnn"
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {'Authorization': f'Bearer {api_key}'}
        
        # Limit text length for summarization
        max_length = 1024
        text_to_summarize = text[:max_length] if len(text) > max_length else text
        
        payload = {
            "inputs": text_to_summarize,
            "parameters": {
                "max_length": 130,
                "min_length": 30,
                "do_sample": False
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                summary = result[0].get('summary_text', '')
                logger.info(f"Summarization successful: {len(summary)} characters")
                return {'success': True, 'summary': summary, 'error': ''}
        
        # API error, provide fallback
        error_msg = f"API error: {response.status_code}"
        summary = text[:200] + "..." if len(text) > 200 else text
        logger.error(f"Summarization failed: {error_msg}, using truncation")
        return {'success': True, 'summary': summary, 'error': ''}
        
    except Exception as e:
        # Exception, provide fallback
        summary = text[:200] + "..." if len(text) > 200 else text
        logger.error(f"Summarization exception: {str(e)}, using truncation")
        return {'success': True, 'summary': summary, 'error': ''}
