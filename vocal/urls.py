from django.urls import path
from . import views

urlpatterns = [
    # UI
    path('ui/', views.vocal_ui, name='vocal_ui'),
    
    # API endpoints
    path('', views.VocalNoteListView.as_view(), name='vocal_list'),
    path('upload/', views.VocalNoteUploadView.as_view(), name='vocal_upload'),
    path('test-api/', views.VocalNoteTestAPIView.as_view(), name='vocal_test_api'),
    path('stats/', views.VocalNoteStatsView.as_view(), name='vocal_stats'),
    path('<int:vocal_id>/', views.VocalNoteDetailView.as_view(), name='vocal_detail'),
    path('<int:vocal_id>/transcribe/', views.VocalNoteTranscribeView.as_view(), name='vocal_transcribe'),
    path('<int:vocal_id>/analyze/', views.VocalNoteAnalyzeView.as_view(), name='vocal_analyze'),
    path('<int:vocal_id>/summarize/', views.VocalNoteSummarizeView.as_view(), name='vocal_summarize'),
    path('<int:vocal_id>/detect-topics/', views.VocalNoteDetectTopicsView.as_view(), name='vocal_detect_topics'),
]
