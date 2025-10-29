from django import forms
from django.forms import inlineformset_factory, RadioSelect
from django.core.exceptions import ValidationError
from datetime import date
from .models import JournalEntry, MediaAsset, Emotion, PersonCategory, Tag


class JournalEntryForm(forms.ModelForm):
    ICON_SCALE_1_5 = [(i, '🙂' * i) for i in range(1, 6)]
    ICON_ENERGY_1_5 = [(i, '⚡' * i) for i in range(1, 6)]
    ICON_SLEEP_1_5 = [(i, '😴' * i) for i in range(1, 6)]

    main_mood_level = forms.TypedChoiceField(
        choices=ICON_SCALE_1_5,
        coerce=int,
        empty_value=None,
        required=True,
        widget=RadioSelect,
        label="Échelle d'humeur (1-5)",
    )
    energy_level = forms.TypedChoiceField(
        choices=ICON_ENERGY_1_5,
        coerce=int,
        empty_value=None,
        required=True,
        widget=RadioSelect,
        label="Niveau d'énergie (1-5)",
    )
    sleep_quality = forms.TypedChoiceField(
        choices=ICON_SLEEP_1_5,
        coerce=int,
        empty_value=None,
        required=True,
        widget=RadioSelect,
        label="Qualité du sommeil (1-5)",
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Tags",
    )
    new_tags = forms.CharField(
        required=False,
        label="Nouveaux tags",
        widget=forms.TextInput(attrs={
            "placeholder": "Ajouter des tags séparés par des virgules (ex: Travail, Santé)",
            "class": "form-control",
        }),
        help_text="Saisie libre: séparés par des virgules",
    )

    class Meta:
        model = JournalEntry
        fields = [
            "title", "content", "entry_date", "time_of_day",
            "mood", "main_mood_level", "energy_level", "sleep_quality",
            "physical_health", "location", "weather", "season",
            "main_subject", "secondary_themes",
            "favorite_moment", "challenge", "achievement", "surprise",
            "daily_goal", "accomplishments", "lesson_learned", "gratitude",
            "physical_activity", "meditation", "screen_time", "meals_quality",
            # M2M handled by explicit fields above: detailed_emotions, people_present, tags
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "Titre de l'entrée",
                "class": "form-control",
            }),
            "content": forms.Textarea(attrs={
                "placeholder": "Écris tes notes ici…",
                "rows": 6,
                "class": "form-control",
            }),
            "entry_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
            }),
            "time_of_day": forms.Select(attrs={"class": "form-control"}),
            "mood": forms.Select(attrs={"class": "form-control"}),
            # radios ci-dessus remplacent les NumberInput
            "physical_health": forms.Select(attrs={"class": "form-control"}),
            "location": forms.Select(attrs={"class": "form-control"}),
            "weather": forms.Select(attrs={"class": "form-control"}),
            "season": forms.Select(attrs={"class": "form-control"}),
            "main_subject": forms.TextInput(attrs={"class": "form-control", "placeholder": "Sujet principal"}),
            "secondary_themes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "favorite_moment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "challenge": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "achievement": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "surprise": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "daily_goal": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "accomplishments": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "lesson_learned": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "gratitude": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "3 choses, une par ligne"}),
            "physical_activity": forms.Select(attrs={"class": "form-control"}),
            "meditation": forms.Select(attrs={"class": "form-control"}),
            "screen_time": forms.Select(attrs={"class": "form-control"}),
            "meals_quality": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre requis côté serveur (même si le modèle autorise blank)
        for fname in [
            "time_of_day", "mood", "physical_health", "location", "weather",
            "season", "physical_activity", "meditation", "screen_time", "meals_quality",
            # Champs demandés comme requis par l'utilisateur
            "main_subject", "secondary_themes",
            "favorite_moment", "challenge", "achievement", "surprise",
            "daily_goal", "accomplishments", "lesson_learned", "gratitude",
        ]:
            if fname in self.fields:
                self.fields[fname].required = True
        labels = {
            "title": "Titre",
            "content": "Contenu",
            "entry_date": "Date",
            "time_of_day": "Heure",
            "mood": "Humeur principale",
            "main_mood_level": "Échelle d'humeur (1-5)",
            "energy_level": "Niveau d'énergie (1-5)",
            "sleep_quality": "Qualité du sommeil (1-5)",
            "physical_health": "Santé physique",
            "location": "Lieu",
            "weather": "Météo",
            "season": "Saison",
            "main_subject": "Sujet principal",
            "secondary_themes": "Thèmes secondaires",
            "favorite_moment": "Moment préféré",
            "challenge": "Défi relevé",
            "achievement": "Réussite",
            "surprise": "Surprise",
            "daily_goal": "Objectif du jour",
            "accomplishments": "Accomplissements",
            "lesson_learned": "Leçon apprise",
            "gratitude": "Gratitude",
            "physical_activity": "Activité physique",
            "meditation": "Méditation",
            "screen_time": "Temps d'écran",
            "meals_quality": "Qualité des repas",
        }

    def clean_main_mood_level(self):
        val = self.cleaned_data.get("main_mood_level")
        if val in ("", None):
            return None
        if not (1 <= int(val) <= 5):
            raise ValidationError("Valeur hors plage (1-5).")
        return val

    def clean_energy_level(self):
        val = self.cleaned_data.get("energy_level")
        if val in ("", None):
            return None
        if not (1 <= int(val) <= 5):
            raise ValidationError("Valeur hors plage (1-5).")
        return val

    def clean_sleep_quality(self):
        val = self.cleaned_data.get("sleep_quality")
        if val in ("", None):
            return None
        if not (1 <= int(val) <= 5):
            raise ValidationError("Valeur hors plage (1-5).")
        return val

    def clean_content(self):
        txt = (self.cleaned_data.get("content") or "").strip()
        if len(txt) > 5000:
            raise ValidationError("Contenu trop long (max 5000 caractères).")
        return txt

    def clean_gratitude(self):
        txt = (self.cleaned_data.get("gratitude") or "").strip()
        if not txt:
            return txt
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        if len(lines) > 3:
            raise ValidationError("Merci de limiter la gratitude à 3 éléments.")
        return "\n".join(lines)

    def clean_new_tags(self):
        raw = (self.cleaned_data.get("new_tags") or "").strip()
        if not raw:
            return raw
        names = [t.strip() for t in raw.split(',') if t.strip()]
        # dédoublonnage insensible à la casse
        seen = set()
        cleaned = []
        for n in names:
            key = n.casefold()
            if key in seen:
                continue
            if len(n) > 50:
                raise ValidationError("Chaque tag doit faire au plus 50 caractères.")
            cleaned.append(n)
            seen.add(key)
        if len(cleaned) > 10:
            raise ValidationError("Merci de limiter l'ajout à 10 nouveaux tags à la fois.")
        return ", ".join(cleaned)

    def clean(self):
        cleaned = super().clean()
        # Au moins 1 tag (existant ou nouveau)
        tags_selected = cleaned.get("tags")
        new_tags_csv = cleaned.get("new_tags", "").strip()
        if (not tags_selected or len(tags_selected) == 0) and not new_tags_csv:
            self.add_error("tags", ValidationError("Merci de choisir au moins un tag ou d'en créer."))
        return cleaned


class MediaAssetForm(forms.ModelForm):
    file = forms.FileField(required=False)
    class Meta:
        model = MediaAsset
        fields = ["file", "caption", "media_type"]
        widgets = {
            "caption": forms.TextInput(attrs={
                "placeholder": "Légende (optionnel)",
                "class": "form-control",
            }),
            "media_type": forms.TextInput(attrs={
                "placeholder": "Type (photo, audio, …)",
                "class": "form-control",
            }),
        }
        labels = {
            "file": "File",
            "caption": "Caption",
            "media_type": "Media type",
        }

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get("file")
        caption = cleaned.get("caption")
        media_type = cleaned.get("media_type")
        # If any metadata provided, require a file
        if (caption or media_type) and not file:
            raise ValidationError("Veuillez choisir un fichier pour ce média.")
        return cleaned

MediaAssetFormSet = inlineformset_factory(
    parent_model=JournalEntry,
    model=MediaAsset,
    form=MediaAssetForm,
    extra=2,
    can_delete=True,
)
