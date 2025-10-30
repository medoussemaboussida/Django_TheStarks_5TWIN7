from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.utils.decorators import method_decorator
from django.db import models as django_models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.authentication import SessionAuthentication
from django.utils import timezone
import os

from .models import VocalNote
from .serializers import VocalNoteSerializer
from .services import transcribe_audio, analyze_sentiment, summarize_text, detect_topics_and_context


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication without CSRF check for API views"""
    def enforce_csrf(self, request):
        return  # Skip CSRF check


@login_required
@ensure_csrf_cookie
def vocal_ui(request):
    """Render the vocal notes UI"""
    return render(request, 'frontend/vocal.html')


class VocalNoteListView(APIView):
    """List all vocal notes for the authenticated user with filtering"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            vocals = VocalNote.objects.filter(user=request.user)
            
            # Apply filters
            category = request.query_params.get('category')
            sentiment = request.query_params.get('sentiment')
            search = request.query_params.get('search')
            
            logger.info(f"Filters: category={category}, sentiment={sentiment}, search={search}")
            
            if category and category != 'all':
                vocals = vocals.filter(category=category)
            
            if sentiment and sentiment != 'all':
                vocals = vocals.filter(sentiment=sentiment)
            
            if search:
                vocals = vocals.filter(
                    django_models.Q(transcription__icontains=search) |
                    django_models.Q(summary__icontains=search) |
                    django_models.Q(context__icontains=search)
                )
            
            serializer = VocalNoteSerializer(vocals, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error loading vocals: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VocalNoteUploadView(APIView):
    """Upload a new vocal note"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        audio_file = request.FILES.get('audio_file')
        if not audio_file:
            return Response({'error': 'No audio file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get duration if provided
        duration = request.data.get('duration')
        
        # Create vocal note
        vocal = VocalNote.objects.create(
            user=request.user,
            audio_file=audio_file,
            duration=float(duration) if duration else None
        )
        
        serializer = VocalNoteSerializer(vocal, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VocalNoteDetailView(APIView):
    """Get or delete a specific vocal note"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, vocal_id):
        try:
            vocal = VocalNote.objects.get(id=vocal_id, user=request.user)
            serializer = VocalNoteSerializer(vocal, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except VocalNote.DoesNotExist:
            return Response({'error': 'Vocal note not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, vocal_id):
        try:
            vocal = VocalNote.objects.get(id=vocal_id, user=request.user)
            # Delete audio file
            if vocal.audio_file:
                if os.path.exists(vocal.audio_file.path):
                    os.remove(vocal.audio_file.path)
            vocal.delete()
            return Response({'message': 'Vocal note deleted successfully'}, status=status.HTTP_200_OK)
        except VocalNote.DoesNotExist:
            return Response({'error': 'Vocal note not found'}, status=status.HTTP_404_NOT_FOUND)


class VocalNoteTranscribeView(APIView):
    """Transcribe a vocal note using Hugging Face Whisper"""
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request, vocal_id):
        try:
            vocal = VocalNote.objects.get(id=vocal_id, user=request.user)
        except VocalNote.DoesNotExist:
            return Response({'error': 'Vocal note not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if audio file exists
        if not vocal.audio_file or not os.path.exists(vocal.audio_file.path):
            return Response({'error': 'Audio file not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Transcribe - always succeeds with fallback
        result = transcribe_audio(vocal.audio_file.path)
        
        # Save transcription (even if it's a fallback message)
        vocal.transcription = result['text']
        vocal.transcribed_at = timezone.now()
        vocal.save()
        
        serializer = VocalNoteSerializer(vocal, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class VocalNoteAnalyzeView(APIView):
    """Analyze sentiment of a transcribed vocal note"""
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request, vocal_id):
        try:
            vocal = VocalNote.objects.get(id=vocal_id, user=request.user)
        except VocalNote.DoesNotExist:
            return Response({'error': 'Vocal note not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if transcription exists
        if not vocal.transcription:
            return Response({'error': 'No transcription available. Please transcribe first.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Analyze sentiment - always succeeds with fallback
        import logging
        logger = logging.getLogger(__name__)
        
        # Debug: Check transcription content
        logger.info(f"=== SENTIMENT ANALYSIS DEBUG ===")
        logger.info(f"Transcription text: '{vocal.transcription}'")
        logger.info(f"Text length: {len(vocal.transcription)}")
        logger.info(f"Is placeholder: {vocal.transcription.startswith('[')}")
        
        # If transcription is a placeholder, show warning
        if vocal.transcription.startswith('['):
            logger.warning("⚠️ Transcription is a placeholder! Real transcription failed.")
            logger.warning("This is why sentiment is neutral - no real text to analyze.")
        
        result = analyze_sentiment(vocal.transcription)
        
        logger.info(f"Sentiment result: {result['sentiment']} ({result['score']})")
        logger.info(f"=== END DEBUG ===")
        
        # Save sentiment (even if it's a fallback)
        vocal.sentiment = result['sentiment']
        vocal.sentiment_score = result['score']
        vocal.analyzed_at = timezone.now()
        vocal.save()
        
        serializer = VocalNoteSerializer(vocal, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class VocalNoteSummarizeView(APIView):
    """Generate summary of a transcribed vocal note"""
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request, vocal_id):
        try:
            vocal = VocalNote.objects.get(id=vocal_id, user=request.user)
        except VocalNote.DoesNotExist:
            return Response({'error': 'Vocal note not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if transcription exists
        if not vocal.transcription:
            return Response({'error': 'No transcription available. Please transcribe first.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Generate summary - always succeeds with fallback
        result = summarize_text(vocal.transcription)
        
        # Save summary (even if it's a fallback)
        vocal.summary = result['summary']
        vocal.save()
        
        serializer = VocalNoteSerializer(vocal, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class VocalNoteTestAPIView(APIView):
    """Test API keys and configuration"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings
        import requests
        
        results = {
            'groq_configured': False,
            'groq_working': False,
            'hf_configured': False,
            'transcription_method': 'none'
        }
        
        # Check Groq
        groq_key = getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'GROK_API_KEY', '')
        groq_base = getattr(settings, 'GROQ_API_BASE', '') or getattr(settings, 'GROK_API_BASE', '')
        
        if groq_key and groq_base:
            results['groq_configured'] = True
            results['groq_key_preview'] = groq_key[:10] + '...'
            results['groq_base'] = groq_base
            
            # Test Groq API
            try:
                url = f"{groq_base.rstrip('/')}/models"
                headers = {'Authorization': f'Bearer {groq_key}'}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    results['groq_working'] = True
                    results['transcription_method'] = 'groq_whisper'
                else:
                    results['groq_error'] = f"Status {response.status_code}"
            except Exception as e:
                results['groq_error'] = str(e)
        
        # Check Hugging Face
        hf_key = getattr(settings, 'HUGGINGFACE_API_KEY', '')
        if hf_key:
            results['hf_configured'] = True
            results['hf_key_preview'] = hf_key[:10] + '...'
            if not results['groq_working']:
                results['transcription_method'] = 'huggingface_whisper'
        
        if not results['groq_configured'] and not results['hf_configured']:
            results['transcription_method'] = 'placeholder_only'
        
        return Response(results, status=status.HTTP_200_OK)


class VocalNoteDetectTopicsView(APIView):
    """Detect topics and context from transcribed vocal note"""
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request, vocal_id):
        try:
            vocal = VocalNote.objects.get(id=vocal_id, user=request.user)
        except VocalNote.DoesNotExist:
            return Response({'error': 'Vocal note not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if transcription exists
        if not vocal.transcription:
            return Response({'error': 'No transcription available. Please transcribe first.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Detect topics and context
        result = detect_topics_and_context(vocal.transcription)
        
        # Save results
        vocal.category = result['category']
        vocal.topics = result['topics']
        vocal.keywords = result['keywords']
        vocal.context = result['context']
        vocal.save()
        
        serializer = VocalNoteSerializer(vocal, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class VocalNoteStatsView(APIView):
    """Get statistics about vocal notes"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        vocals = VocalNote.objects.filter(user=request.user)
        
        total = vocals.count()
        transcribed = vocals.exclude(transcription__isnull=True).exclude(transcription='').count()
        analyzed = vocals.exclude(sentiment__isnull=True).count()
        
        # Sentiment breakdown
        positive = vocals.filter(sentiment='positive').count()
        neutral = vocals.filter(sentiment='neutral').count()
        negative = vocals.filter(sentiment='negative').count()
        
        # Total duration
        total_duration = sum([v.duration for v in vocals if v.duration]) or 0
        
        return Response({
            'total_vocals': total,
            'transcribed': transcribed,
            'analyzed': analyzed,
            'sentiment_breakdown': {
                'positive': positive,
                'neutral': neutral,
                'negative': negative
            },
            'total_duration_seconds': round(total_duration, 2)
        }, status=status.HTTP_200_OK)
