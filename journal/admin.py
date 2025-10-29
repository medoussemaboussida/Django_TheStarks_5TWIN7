from django.contrib import admin
from .models import JournalEntry, MediaAsset, Emotion, PersonCategory, Tag


class MediaAssetInline(admin.TabularInline):
    model = MediaAsset
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "entry_date", "mood", "created_at")
    list_filter = ("user", "entry_date", "mood")
    search_fields = ("title", "content")
    inlines = [MediaAssetInline]


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("entry", "file", "media_type", "uploaded_at")


@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(PersonCategory)
class PersonCategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)

# Register your models here.
