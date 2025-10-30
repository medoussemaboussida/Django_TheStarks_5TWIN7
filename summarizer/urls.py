from django.urls import path
from .views import (
    summarizer_list,
    summarizer_create, summarizer_update, summarizer_delete, summarizer_generate
)

urlpatterns = [
    path('', summarizer_list, name='summarizer_list'),
    path('create/', summarizer_create, name='summarizer_create'),
    path('<int:pk>/update/', summarizer_update, name='summarizer_update'),
    path('<int:pk>/delete/', summarizer_delete, name='summarizer_delete'),
    path('<int:pk>/generate/', summarizer_generate, name='summarizer_generate'),
]