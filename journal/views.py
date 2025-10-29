from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from django.db.models import Q
from .models import JournalEntry, Tag
from .forms import JournalEntryForm, MediaAssetFormSet
from .ai_provider import recommend_activities_gemini


@login_required
def entry_list(request):
    q = request.GET.get('q', '').strip()
    entries = JournalEntry.objects.filter(user=request.user)
    if q:
        entries = entries.filter(
            Q(title__icontains=q) | Q(content__icontains=q) | Q(entry_date__icontains=q)
        )
    return render(request, 'journal/entry_list.html', {'entries': entries, 'q': q})


@login_required
def entry_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    # Use Google Gemini for real AI recommendations (free tier personal)
    rec_obj = recommend_activities_gemini(entry)
    recommendations = rec_obj.get("activities", []) if isinstance(rec_obj, dict) else []
    rec_loading = bool(rec_obj.get("loading")) if isinstance(rec_obj, dict) else False
    rec_error = rec_obj.get("error") if isinstance(rec_obj, dict) else None
    return render(request, 'journal/entry_detail.html', {
        'entry': entry,
        'recommendations': recommendations,
        'rec_loading': rec_loading,
        'rec_error': rec_error,
    })


@login_required
def entry_create(request):
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        formset = MediaAssetFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            # Save M2M fields
            form.instance = entry
            form.save_m2m()
            # Handle free-text tags
            new_tags_csv = form.cleaned_data.get('new_tags', '')
            if new_tags_csv:
                for name in [t.strip() for t in new_tags_csv.split(',') if t.strip()]:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    entry.tags.add(tag)
            formset.instance = entry
            formset.save()
            return redirect('journal:entry_detail', pk=entry.pk)
    else:
        form = JournalEntryForm()
        formset = MediaAssetFormSet()
    return render(request, 'journal/entry_form.html', {'form': form, 'formset': formset})


@login_required
def entry_update(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=entry)
        formset = MediaAssetFormSet(request.POST, request.FILES, instance=entry)
        if form.is_valid() and formset.is_valid():
            # Sauvegarde d'abord sans M2M, puis M2M via save_m2m (nécessite commit=False)
            entry = form.save(commit=False)
            entry.save()
            form.save_m2m()
            # Handle free-text tags
            new_tags_csv = form.cleaned_data.get('new_tags', '')
            if new_tags_csv:
                for name in [t.strip() for t in new_tags_csv.split(',') if t.strip()]:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    entry.tags.add(tag)
            formset.save()
            return redirect('journal:entry_detail', pk=entry.pk)
    else:
        form = JournalEntryForm(instance=entry)
        formset = MediaAssetFormSet(instance=entry)
    return render(request, 'journal/entry_form.html', {'form': form, 'formset': formset, 'entry': entry})


@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('journal:entry_list')
    return render(request, 'journal/entry_confirm_delete.html', {'entry': entry})

def _local_activity_recommendations(entry):
    """Local, free recommendations based on entry fields. No external API, no prompt.
    Returns a list of {label, why, duration_min, category}.
    """
    def level(val):
        try:
            return int(val) if val is not None else 0
        except Exception:
            return 0

    energy = level(getattr(entry, 'energy_level', None))
    sleep = level(getattr(entry, 'sleep_quality', None))
    mood = level(getattr(entry, 'main_mood_level', None))
    weather = getattr(entry, 'weather', '') or ''
    screen = (getattr(entry, 'screen_time', '') or '').upper()
    activity = (getattr(entry, 'physical_activity', '') or '').upper()
    themes = (entry.secondary_themes or '').lower()
    goal = (entry.daily_goal or '').strip()

    recs = []
    def add(label, why, duration_min, category):
        recs.append({
            'label': label,
            'why': why,
            'duration_min': duration_min,
            'category': category,
        })

    # Base rules by energy/sleep
    if energy <= 2 and sleep <= 2:
        add("Regarder un film/épisode relax", "Énergie et sommeil bas — privilégier la détente", 90, "loisir")
        add("Méditation/respiration 10 min", "Aide à récupérer avec faible énergie", 10, "bien-etre")
    elif energy >= 4 and sleep >= 3:
        add("Sport 30 min (course/marche rapide)", "Bonne énergie et sommeil correct", 30, "bien-etre")
        add("Tâche objectif 25 min (Pomodoro)", "Capitaliser sur l'énergie pour avancer", 25, "productivite")
    else:
        add("Marche 15–20 min", "Remettre le corps en mouvement sans forcer", 20, "bien-etre")

    # Weather influence
    if weather.upper() in ("SUNNY", "ENSOLEILLÉ", "ENSOLEILLE") and energy >= 3:
        add("Sortie au parc / café en terrasse", "Météo ensoleillée et énergie suffisante", 30, "social")
    if weather.upper() in ("RAINY", "PLUIE", "PLUVIEUX"):
        add("Lecture 20 min / boisson chaude", "Météo pluvieuse — activité intérieure apaisante", 20, "loisir")

    # Screen time hygiene
    if screen in ("5H+", "5H_PLUS", "HIGH"):
        add("Activité sans écran (cuisine, dessin)", "Temps d'écran élevé — réduire l'exposition", 30, "bien-etre")

    # Stress / challenges in themes
    if any(k in themes for k in ["stress", "anx", "pression", "fatigue"]):
        add("Respiration 4-4-4-4", "Thèmes stress/fatigue détectés", 5, "bien-etre")

    # Goal-oriented suggestion
    if goal:
        add("Petit pas vers l'objectif (10–20 min)", "Avancer concrètement: %s" % goal[:60], 15, "productivite")

    # Ensure unique by label
    seen = set()
    unique = []
    for r in recs:
        if r['label'] in seen:
            continue
        seen.add(r['label'])
        unique.append(r)
    return unique[:5]

# Create your views here.
