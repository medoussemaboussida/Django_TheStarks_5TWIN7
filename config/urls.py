"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core import views
from core.forms import PasswordResetRequestForm, StyledSetPasswordForm
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.root, name='root'),
    path('login/', views.login_view, name='login'),
    path('home/', views.frontend_home, name='frontend_home'),
    path('profile/', views.profile_view, name='profile'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-template/', views.admin_dashboard, name='admin_dashboard'),
    path('summarizer/', include('summarizer.urls')),  # Ajout ici pour inclure les URLs de l'app summarizer
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='admin/password_reset_form.html',
        form_class=PasswordResetRequestForm
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='admin/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='admin/password_reset_confirm.html',
        form_class=StyledSetPasswordForm
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='admin/password_reset_complete.html'
    ), name='password_reset_complete'),
]
