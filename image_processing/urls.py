from django.urls import path
from . import views

urlpatterns = [
    path('', views.ImageListView.as_view(), name='image_list'),
    path('upload/', views.ImageUploadView.as_view(), name='image_upload'),
    path('analyze/', views.ImageAnalyzeView.as_view(), name='image_analyze'),
    path('generate/', views.ImageGenerateView.as_view(), name='image_generate'),
    path('ui/', views.images_ui, name='images_ui'),
    path('stats/', views.ImageStatsView.as_view(), name='image_stats'),
    path('generated/', views.GeneratedListView.as_view(), name='generated_list'),
    # CRUD operations
    path('<int:image_id>/', views.ImageDetailView.as_view(), name='image_detail'),
    path('generated/<int:image_id>/', views.GeneratedImageDetailView.as_view(), name='generated_detail'),
    # AI features
    path('describe/', views.ImageDescribeView.as_view(), name='image_describe'),
    path('enhance/', views.ImageEnhanceView.as_view(), name='image_enhance'),
    path('variation/', views.ImageVariationView.as_view(), name='image_variation'),
    # Filters and adjustments
    path('filter/', views.ImageFilterView.as_view(), name='image_filter'),
    # AI Analysis
    path('ai-analysis/', views.ImageAIAnalysisView.as_view(), name='image_ai_analysis'),
    path('detect-objects/', views.ImageObjectDetectionView.as_view(), name='image_detect_objects'),
    path('ocr/', views.ImageOCRView.as_view(), name='image_ocr'),
    path('caption/', views.ImageCaptionView.as_view(), name='image_caption'),
    path('exif/', views.ImageEXIFView.as_view(), name='image_exif'),
]
