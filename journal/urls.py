from django.urls import path
from . import views

app_name = "journal"

urlpatterns = [
    path("", views.entry_list, name="entry_list"),
    path("create/", views.entry_create, name="entry_create"),
    # Routes explicites pour éviter conflit avec <int:pk>/
    path("edit/<int:pk>/", views.entry_update, name="entry_update"),
    path("delete/<int:pk>/", views.entry_delete, name="entry_delete"),
    path("<int:pk>/", views.entry_detail, name="entry_detail"),
    
]
