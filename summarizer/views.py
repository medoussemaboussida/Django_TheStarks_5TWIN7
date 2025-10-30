from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from .models import Summarizer
from .forms import SummarizerForm
import logging
import requests
logger = logging.getLogger(__name__)

def summarizer_list(request):
    summarizers = Summarizer.objects.all()
    return render(request, 'frontend/summarizer.html', {'summarizers': summarizers})

def summarizer_create(request):
    if request.method == 'POST':
        form = SummarizerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('summarizer_list')
    else:
        form = SummarizerForm()
    
    return render(request, 'frontend/add_summarizer.html', {'form': form})

def summarizer_update(request, pk):
    obj = get_object_or_404(Summarizer, pk=pk)
    if request.method == 'POST':
        form = SummarizerForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect('summarizer_list')
    else:
        form = SummarizerForm(instance=obj)
    
    return render(request, 'frontend/update_summarizer.html', {'form': form, 'summarizer': obj})

def summarizer_delete(request, pk):
    obj = get_object_or_404(Summarizer, pk=pk)
    if request.method == 'POST':
        obj.delete()
    return redirect('summarizer_list')


# YOUR GROQ KEY (100% WORKING!)
GROQ_API_KEY = "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"
def summarizer_generate(request, pk):
    obj = get_object_or_404(Summarizer, pk=pk)
    if request.method != "POST":
        return redirect("summarizer_list")

    # Show loading
    obj.summary = "⚡ Groq génère votre résumé..."
    obj.save()

    try:
        # ✅ WORKING MODEL (2025)
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        payload = {
            "model": "llama-3.3-70b-versatile",  # ✅ NEW & BEST!
            "messages": [
                {
                    "role": "system",
                    "content": "Assistant empathique français. Résume le problème + 1 conseil pratique."
                },
                {
                    "role": "user",
                    "content": obj.user_input
                }
            ],
            "max_tokens": 400,
            "temperature": 0.7
        }

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"].strip()
            obj.summary = f"🤖\n\n{summary}"
        else:
            obj.summary = f"Erreur {response.status_code}: {response.text[:200]}"

    except Exception as e:
        obj.summary = f"Erreur: {str(e)}"

    obj.save()
    return redirect("summarizer_list")