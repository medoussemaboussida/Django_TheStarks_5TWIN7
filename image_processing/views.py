from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import ImageModel, GeneratedImage
from .serializers import ImageModelSerializer, GeneratedImageSerializer
from .services.face_detection import detect_faces_and_tags
from .services.image_generation import generate_illustration
from PIL import Image
from io import BytesIO


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        file = request.FILES.get('image')
        if not file:
            return Response({'error': 'image file is required'}, status=status.HTTP_400_BAD_REQUEST)

        obj = ImageModel.objects.create(user=request.user, image=file)

        # Generate thumbnail
        try:
            img = Image.open(obj.image)
            img.thumbnail((320, 320))
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            obj.thumbnail.save(f"thumb_{timezone.now().timestamp()}.jpg", ContentFile(buffer.getvalue()), save=False)
        except Exception:
            pass

        # Auto-tag via face detection
        try:
            tags = detect_faces_and_tags(obj.image.path)
            obj.tags = tags
        except Exception:
            obj.tags = {}

        obj.save()
        return Response(ImageModelSerializer(obj).data, status=status.HTTP_201_CREATED)


class ImageAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        image_id = request.data.get('image_id')
        file = request.FILES.get('image')
        if not image_id and not file:
            return Response({'error': 'provide image_id or upload image'}, status=status.HTTP_400_BAD_REQUEST)

        if image_id:
            try:
                obj = ImageModel.objects.get(id=image_id, user=request.user)
                path = obj.image.path
            except ImageModel.DoesNotExist:
                return Response({'error': 'image not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            tmp = ImageModel.objects.create(user=request.user, image=file)
            path = tmp.image.path

        try:
            tags = detect_faces_and_tags(path)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if image_id:
            obj.tags = tags
            obj.save()

        return Response({'tags': tags}, status=status.HTTP_200_OK)


class ImageGenerateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        description = request.data.get('description', '').strip()
        if not description:
            return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            override = (request.data.get('provider') or '').strip().lower()
            provider = override if override and override != 'auto' else (getattr(settings, 'AI_PROVIDER', '') or 'local')
            api_key = getattr(settings, 'AI_API_KEY', '') or getattr(settings, 'GROK_API_KEY', '') or getattr(settings, 'GROQ_API_KEY', '')
            api_base = getattr(settings, 'AI_API_BASE', '') or getattr(settings, 'GROK_API_BASE', '') or getattr(settings, 'GROQ_API_BASE', '')
            img_bytes, ext, meta = generate_illustration(description, api_key=api_key, api_base=api_base, provider=provider)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        # Save generated image
        gen = GeneratedImage(user=request.user, description=description)
        gen.image.save(f"gen_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}", ContentFile(img_bytes))
        gen.save()
        payload = {
            **GeneratedImageSerializer(gen).data,
            'meta': meta,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class ImageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters for filtering and search
        search = request.query_params.get('search', '').strip()
        quality = request.query_params.get('quality', '').strip()
        has_faces = request.query_params.get('has_faces', '').strip()
        sort_by = request.query_params.get('sort_by', '-uploaded_at')
        
        images = ImageModel.objects.filter(user=request.user)
        
        # Search by ID or tags
        if search:
            from django.db.models import Q
            images = images.filter(
                Q(id__icontains=search) | 
                Q(tags__icontains=search)
            )
        
        # Filter by quality
        if quality in ['good', 'medium', 'none']:
            images = images.filter(tags__quality=quality)
        
        # Filter by face presence
        if has_faces == 'yes':
            images = images.exclude(tags__contains_face='no_face')
        elif has_faces == 'no':
            images = images.filter(tags__contains_face='no_face')
        
        # Sort
        valid_sorts = ['-created_at', 'created_at', '-id', 'id']
        if sort_by in valid_sorts:
            images = images.order_by(sort_by)
        else:
            images = images.order_by('-created_at')
        
        from .serializers import ImageModelSerializer
        data = ImageModelSerializer(images, many=True).data
        return Response(data, status=status.HTTP_200_OK)


@login_required
@ensure_csrf_cookie
def images_ui(request):
    return render(request, 'frontend/images.html')


class ImageDetailView(APIView):
    """Get, update or delete a specific image"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request, image_id):
        try:
            from .serializers import ImageModelSerializer
            img = ImageModel.objects.get(id=image_id, user=request.user)
            return Response(ImageModelSerializer(img).data, status=status.HTTP_200_OK)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, image_id):
        """Update image tags or metadata"""
        try:
            from .serializers import ImageModelSerializer
            img = ImageModel.objects.get(id=image_id, user=request.user)
            tags = request.data.get('tags')
            if tags and isinstance(tags, dict):
                img.tags = {**img.tags, **tags} if img.tags else tags
                img.save()
            return Response(ImageModelSerializer(img).data, status=status.HTTP_200_OK)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, image_id):
        """Delete an image"""
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
            img.delete()
            return Response({'message': 'Image deleted successfully'}, status=status.HTTP_200_OK)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)


class GeneratedImageDetailView(APIView):
    """Delete a generated image"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, image_id):
        try:
            img = GeneratedImage.objects.get(id=image_id, user=request.user)
            img.delete()
            return Response({'message': 'Generated image deleted successfully'}, status=status.HTTP_200_OK)
        except GeneratedImage.DoesNotExist:
            return Response({'error': 'Generated image not found'}, status=status.HTTP_404_NOT_FOUND)


class ImageStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Avg
        total = ImageModel.objects.filter(user=request.user).count()
        generated = GeneratedImage.objects.filter(user=request.user).count()
        # average faces from tags.count when present
        images = ImageModel.objects.filter(user=request.user)
        counts = []
        for im in images:
            try:
                c = (im.tags or {}).get('count')
                if isinstance(c, int):
                    counts.append(c)
            except Exception:
                pass
        avg_faces = (sum(counts) / len(counts)) if counts else 0.0
        return Response({
            'total_images': total,
            'generated_images': generated,
            'average_faces_per_image': round(avg_faces, 2),
        }, status=status.HTTP_200_OK)


class GeneratedListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        gens = GeneratedImage.objects.filter(user=request.user).order_by('-created_at')
        data = GeneratedImageSerializer(gens, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class ImageDescribeView(APIView):
    """Generate detailed AI description of an image using Groq text model"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        image_id = request.data.get('image_id')
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            import requests
            
            api_key = getattr(settings, 'GROK_API_KEY', '') or getattr(settings, 'GROQ_API_KEY', '')
            api_base = getattr(settings, 'GROK_API_BASE', '') or getattr(settings, 'GROQ_API_BASE', '')
            
            if not api_key or not api_base:
                return Response({'error': 'Groq API not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Use tags and metadata to generate description
            tags = img.tags or {}
            face_info = tags.get('contains_face', 'no_face')
            count = tags.get('count', 0)
            quality = tags.get('quality', 'unknown')
            
            # Build detailed context
            context = []
            if face_info == 'contains_face' and count == 1:
                context.append(f"portrait of one person")
            elif face_info == 'multiple_faces' and count > 1:
                context.append(f"group photo with {count} people")
            else:
                context.append("scene or landscape")
            
            if quality == 'good':
                context.append("high quality")
            elif quality == 'medium':
                context.append("decent quality")
            
            prompt = f"You are a professional photographer. Describe an image that is a {', '.join(context)}. Write a vivid, poetic description in 3-4 sentences covering: the subjects, setting, lighting, mood, and artistic style. Be specific and evocative."
            
            url = f"{api_base.rstrip('/')}/chat/completions"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a professional photographer and art critic with expertise in visual storytelling."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 250,
                "temperature": 0.7
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                description = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return Response({'description': description}, status=status.HTTP_200_OK)
            else:
                # Fallback to generic description
                fallback = f"Image #{img.id} with {face_info.replace('_', ' ')}. "
                if count > 0:
                    fallback += f"Contains {count} person(s). "
                fallback += "A captured moment preserved in pixels."
                return Response({'description': fallback}, status=status.HTTP_200_OK)
        except Exception as e:
            # Fallback description
            fallback = f"Image #{img.id}. A visual story waiting to be told."
            return Response({'description': fallback}, status=status.HTTP_200_OK)


class ImageEnhanceView(APIView):
    """Get AI suggestions for image enhancement using Groq text model"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        image_id = request.data.get('image_id')
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            import requests
            import json
            
            api_key = getattr(settings, 'GROK_API_KEY', '') or getattr(settings, 'GROQ_API_KEY', '')
            api_base = getattr(settings, 'GROK_API_BASE', '') or getattr(settings, 'GROQ_API_BASE', '')
            
            if not api_key or not api_base:
                return Response({'error': 'Groq API not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Use tags to generate contextual suggestions
            tags = img.tags or {}
            quality = tags.get('quality', 'unknown')
            face_count = tags.get('count', 0)
            contains_face = tags.get('contains_face', 'no_face')
            
            # Build specific context
            image_type = "portrait" if face_count > 0 else "landscape/scene"
            quality_desc = {"good": "high quality", "medium": "medium quality", "none": "needs improvement"}.get(quality, "unknown quality")
            
            prompt = f"""Analyze a {image_type} photograph with {quality_desc}.
            {f'It contains {face_count} person(s).' if face_count > 0 else 'No people visible.'}
            
            Provide professional enhancement suggestions in this exact JSON format:
            {{
              "brightness": "specific tip",
              "contrast": "specific tip",
              "composition": "specific tip",
              "overall_quality": "rating/10"
            }}
            
            Be specific and actionable. Return ONLY the JSON, no other text."""
            
            url = f"{api_base.rstrip('/')}/chat/completions"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a professional photographer and photo editor. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 250,
                "temperature": 0.2
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                # Parse JSON from response
                content = content.strip()
                if content.startswith('```'):
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                content = content.strip('`').strip()
                try:
                    suggestions = json.loads(content)
                except:
                    suggestions = {
                        "brightness": "Adjust based on lighting conditions",
                        "contrast": "Enhance to make subjects stand out",
                        "composition": "Follow rule of thirds",
                        "overall_quality": f"{quality}"
                    }
                return Response({'suggestions': suggestions}, status=status.HTTP_200_OK)
            else:
                # Fallback suggestions
                suggestions = {
                    "brightness": "Optimize lighting for better visibility",
                    "contrast": "Increase contrast to enhance depth",
                    "composition": "Consider rule of thirds for balance",
                    "overall_quality": f"{quality} - Good baseline"
                }
                return Response({'suggestions': suggestions}, status=status.HTTP_200_OK)
        except Exception as e:
            # Fallback suggestions
            suggestions = {
                "brightness": "Adjust as needed",
                "contrast": "Fine-tune for clarity",
                "composition": "Frame your subject well",
                "overall_quality": "Analyze complete"
            }
            return Response({'suggestions': suggestions}, status=status.HTTP_200_OK)


class ImageVariationView(APIView):
    """Generate variations of an image using AI providers"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        image_id = request.data.get('image_id')
        style = request.data.get('style', 'artistic')
        
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            import requests
            from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter
            from io import BytesIO
            
            # Get image tags for context
            tags = img.tags or {}
            face_count = tags.get('count', 0)
            
            # Build descriptive prompt
            if face_count > 0:
                base_prompt = f"portrait of {face_count} person(s)"
            else:
                base_prompt = "image scene"
            
            prompt = f"{base_prompt}, {style} style, high quality, detailed"
            
            # Try Pollinations first (most reliable, no auth)
            try:
                import random
                prompt_encoded = requests.utils.quote(prompt)
                seed = random.randint(1, 1000000)
                url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=512&height=512&seed={seed}&nologo=true"
                resp = requests.get(url, timeout=45)
                if resp.status_code == 200:
                    gen = GeneratedImage(user=request.user, description=f"Variation ({style}): {prompt}")
                    gen.image.save(f"var_{timezone.now().strftime('%Y%m%d%H%M%S')}.png", ContentFile(resp.content))
                    gen.save()
                    return Response(GeneratedImageSerializer(gen).data, status=status.HTTP_201_CREATED)
            except Exception:
                pass
            
            # Try Hugging Face as fallback
            hf_key = getattr(settings, 'HUGGINGFACE_API_KEY', '')
            if hf_key:
                try:
                    model = "stabilityai/stable-diffusion-2-1"
                    url = f"https://api-inference.huggingface.co/models/{model}"
                    headers = {'Authorization': f'Bearer {hf_key}'}
                    resp = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=60)
                    if resp.status_code == 200:
                        gen = GeneratedImage(user=request.user, description=f"Variation ({style}): {prompt}")
                        gen.image.save(f"var_{timezone.now().strftime('%Y%m%d%H%M%S')}.png", ContentFile(resp.content))
                        gen.save()
                        return Response(GeneratedImageSerializer(gen).data, status=status.HTTP_201_CREATED)
                except Exception:
                    pass
            
            # Final fallback: Create stylized placeholder
            original = PILImage.open(img.image.path)
            original = original.convert('RGB')
            original.thumbnail((512, 512))
            
            # Apply style effects
            if style == 'cartoon':
                original = original.filter(ImageFilter.EDGE_ENHANCE_MORE)
            elif style == 'watercolor':
                original = original.filter(ImageFilter.SMOOTH_MORE)
            elif style == 'artistic':
                original = original.filter(ImageFilter.CONTOUR)
            
            # Add style label
            draw = ImageDraw.Draw(original)
            try:
                font = ImageFont.load_default()
            except:
                font = None
            draw.text((10, 10), f"Style: {style}", fill=(255, 255, 255), font=font)
            
            buf = BytesIO()
            original.save(buf, format='PNG')
            
            gen = GeneratedImage(user=request.user, description=f"Variation ({style}): Filtered version")
            gen.image.save(f"var_{timezone.now().strftime('%Y%m%d%H%M%S')}.png", ContentFile(buf.getvalue()))
            gen.save()
            return Response(GeneratedImageSerializer(gen).data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageFilterView(APIView):
    """Apply filters and adjustments to images"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Filter request: {request.data}")
        from .services.image_filters import (
            adjust_brightness, adjust_contrast, adjust_saturation, adjust_sharpness,
            apply_blur, apply_sharpen, apply_edge_enhance, convert_to_grayscale,
            apply_sepia, rotate_image, flip_image, apply_auto_enhance,
            apply_cartoon_effect, apply_sketch_effect
        )
        
        image_id = request.data.get('image_id')
        filter_type = request.data.get('filter_type')
        filter_value = request.data.get('value', 1.0)
        
        if not image_id or not filter_type:
            return Response({'error': 'image_id and filter_type are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
            image_path = img.image.path
            logger.info(f"Image found: {image_path}")
            logger.info(f"Filter type: {filter_type}, value: {filter_value}")
            
            # Apply the requested filter
            if filter_type == 'brightness':
                result_bytes = adjust_brightness(image_path, float(filter_value))
            elif filter_type == 'contrast':
                result_bytes = adjust_contrast(image_path, float(filter_value))
            elif filter_type == 'saturation':
                result_bytes = adjust_saturation(image_path, float(filter_value))
            elif filter_type == 'sharpness':
                result_bytes = adjust_sharpness(image_path, float(filter_value))
            elif filter_type == 'blur':
                result_bytes = apply_blur(image_path, int(filter_value))
            elif filter_type == 'sharpen':
                result_bytes = apply_sharpen(image_path)
            elif filter_type == 'edge_enhance':
                result_bytes = apply_edge_enhance(image_path)
            elif filter_type == 'grayscale':
                result_bytes = convert_to_grayscale(image_path)
            elif filter_type == 'sepia':
                result_bytes = apply_sepia(image_path)
            elif filter_type == 'rotate':
                result_bytes = rotate_image(image_path, int(filter_value))
            elif filter_type == 'flip_horizontal':
                result_bytes = flip_image(image_path, 'horizontal')
            elif filter_type == 'flip_vertical':
                result_bytes = flip_image(image_path, 'vertical')
            elif filter_type == 'auto_enhance':
                result_bytes = apply_auto_enhance(image_path)
            elif filter_type == 'cartoon':
                result_bytes = apply_cartoon_effect(image_path)
            elif filter_type == 'sketch':
                result_bytes = apply_sketch_effect(image_path)
            else:
                return Response({'error': f'Unknown filter type: {filter_type}'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Save as new generated image
            gen = GeneratedImage(
                user=request.user,
                description=f"Filtered: {filter_type} applied to image #{image_id}"
            )
            filename = f"filtered_{filter_type}_{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
            gen.image.save(filename, ContentFile(result_bytes))
            gen.save()
            
            return Response(GeneratedImageSerializer(gen).data, status=status.HTTP_201_CREATED)
            
        except ImageModel.DoesNotExist:
            logger.error(f"Image not found: {image_id}")
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Filter error: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageAIAnalysisView(APIView):
    """Comprehensive AI analysis of images"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        from .services.ai_analysis import comprehensive_analysis
        import logging
        logger = logging.getLogger(__name__)
        
        image_id = request.data.get('image_id')
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
            logger.info(f"Starting AI analysis for image {image_id}: {img.image.path}")
            
            result = comprehensive_analysis(img.image.path)
            
            logger.info(f"AI analysis completed: success={result.get('success')}")
            
            # Update image tags with AI suggestions
            if result['success'] and result['summary']['suggested_tags']:
                img.tags = {
                    **img.tags,
                    'ai_tags': result['summary']['suggested_tags'],
                    'scene_type': result['summary']['scene_type'],
                    'has_people': result['summary']['has_people'],
                    'has_text': result['summary']['has_text'],
                    'emotion': result['summary']['dominant_emotion']
                }
                img.save()
            
            return Response(result, status=status.HTTP_200_OK)
            
        except ImageModel.DoesNotExist:
            logger.error(f"Image {image_id} not found for AI analysis")
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"AI analysis error: {str(e)}", exc_info=True)
            return Response({'error': f'Analysis failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageObjectDetectionView(APIView):
    """Detect objects and people in image"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        from .services.ai_analysis import detect_objects_and_people
        
        image_id = request.data.get('image_id')
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
            result = detect_objects_and_people(img.image.path)
            return Response(result, status=status.HTTP_200_OK)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageOCRView(APIView):
    """Extract text from image"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        from .services.ai_analysis import extract_text_ocr
        
        image_id = request.data.get('image_id')
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
            result = extract_text_ocr(img.image.path)
            
            # Save extracted text to tags
            if result['success'] and result['has_text']:
                img.tags = {**img.tags, 'extracted_text': result['text']}
                img.save()
            
            return Response(result, status=status.HTTP_200_OK)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageCaptionView(APIView):
    """Generate automatic caption for image"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        from .services.ai_analysis import generate_caption
        
        image_id = request.data.get('image_id')
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
            result = generate_caption(img.image.path)
            
            # Save caption to tags
            if result['success']:
                img.tags = {
                    **img.tags,
                    'auto_caption': result['caption'],
                    'detailed_caption': result['detailed_caption']
                }
                img.save()
            
            return Response(result, status=status.HTTP_200_OK)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageEXIFView(APIView):
    """Extract EXIF metadata including GPS"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        from .services.ai_analysis import extract_exif_metadata
        
        image_id = request.data.get('image_id')
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = ImageModel.objects.get(id=image_id, user=request.user)
            result = extract_exif_metadata(img.image.path)
            
            # Save GPS to tags
            if result['success'] and result['has_gps']:
                img.tags = {
                    **img.tags,
                    'gps_latitude': result['latitude'],
                    'gps_longitude': result['longitude']
                }
                img.save()
            
            return Response(result, status=status.HTTP_200_OK)
        except ImageModel.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
