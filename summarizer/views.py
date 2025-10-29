from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from .models import Summarizer
from .forms import SummarizerForm

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