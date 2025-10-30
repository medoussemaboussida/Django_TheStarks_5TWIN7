from rest_framework import serializers
from .models import VocalNote


class VocalNoteSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    
    class Meta:
        model = VocalNote
        fields = [
            'id', 'user', 'audio_file', 'audio_url', 'duration',
            'transcription', 'transcribed_at',
            'sentiment', 'sentiment_score', 'analyzed_at',
            'summary', 'category', 'topics', 'keywords', 'context',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'transcription', 'transcribed_at',
            'sentiment', 'sentiment_score', 'analyzed_at',
            'summary', 'category', 'topics', 'keywords', 'context',
            'created_at', 'updated_at'
        ]
    
    def get_audio_url(self, obj):
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None
