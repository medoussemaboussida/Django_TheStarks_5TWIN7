from django import forms
from .models import Summarizer

class SummarizerForm(forms.ModelForm):
    class Meta:
        model = Summarizer
        fields = ['title', 'user_input', 'summary']  # Champs éditables
        widgets = {
            'user_input': forms.Textarea(attrs={'rows': 5}),
            'summary': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Ce champ sera rempli automatiquement par l\'IA plus tard.'}),
        }