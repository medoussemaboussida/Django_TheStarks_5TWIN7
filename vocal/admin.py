from django.contrib import admin
from .models import VocalNote


@admin.register(VocalNote)
class VocalNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'duration', 'sentiment', 'sentiment_score', 'created_at']
    list_filter = ['sentiment', 'created_at']
    search_fields = ['user__username', 'transcription']
    readonly_fields = ['created_at', 'updated_at', 'transcribed_at', 'analyzed_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'audio_file', 'duration', 'created_at', 'updated_at')
        }),
        ('Transcription', {
            'fields': ('transcription', 'transcribed_at')
        }),
        ('Analysis', {
            'fields': ('sentiment', 'sentiment_score', 'analyzed_at', 'summary')
        }),
    )
