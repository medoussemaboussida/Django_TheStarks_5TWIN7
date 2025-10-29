from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
import re
from datetime import datetime, date
from .forms import SignupForm, EmailAuthForm
from django.conf import settings
import json
import urllib.parse
import urllib.request

def admin_dashboard(request):
    return render(request, 'admin/index.html')

def frontend_home(request):
    return render(request, 'frontend/index.html')

def root(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return render(request, 'frontend/index.html')
    return login_view(request)

def login_view(request):
    if request.method == 'POST':
        form = EmailAuthForm(request.POST)
        # reCAPTCHA verification if keys are configured
        site_key = getattr(settings, 'RECAPTCHA_SITE_KEY', '')
        secret_key = getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
        if site_key and secret_key:
            recaptcha_response = request.POST.get('g-recaptcha-response', '')
            if not recaptcha_response:
                messages.error(request, 'Veuillez valider le reCAPTCHA.')
                return render(request, 'admin/login.html', {'form': form, 'recaptcha_site_key': site_key})
            data = urllib.parse.urlencode({
                'secret': secret_key,
                'response': recaptcha_response,
                'remoteip': request.META.get('REMOTE_ADDR', ''),
            }).encode()
            req = urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=data)
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    result = json.loads(resp.read().decode())
                if not result.get('success'):
                    messages.error(request, 'La vérification reCAPTCHA a échoué. Réessayez.')
                    return render(request, 'admin/login.html', {'form': form, 'recaptcha_site_key': site_key})
            except Exception:
                messages.error(request, "Impossible de vérifier le reCAPTCHA pour le moment.")
                return render(request, 'admin/login.html', {'form': form, 'recaptcha_site_key': site_key})
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('root')
        else:
            messages.error(request, 'Identifiants invalides')
    else:
        form = EmailAuthForm()
    return render(request, 'admin/login.html', {'form': form, 'recaptcha_site_key': getattr(settings, 'RECAPTCHA_SITE_KEY', '')})

def register_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Compte créé avec succès. Connectez-vous.')
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'admin/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('root')

def profile_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    profile = getattr(request.user, 'profile', None)
    if request.method == 'POST':
        errors = {}
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        birth_date = request.POST.get('birth_date', '').strip()

        if username and username != request.user.username:
            # pattern: letters, numbers, dot, underscore, dash; length 3..30
            if not re.fullmatch(r'[A-Za-z0-9._-]{3,30}', username):
                errors['username'] = "Nom d’utilisateur invalide (3-30 caractères, lettres/chiffres . _ -)."
            if User.objects.filter(username__iexact=username).exclude(pk=request.user.pk).exists():
                errors['username'] = "Ce nom d’utilisateur est déjà pris."
            if 'username' not in errors:
                request.user.username = username

        # Full name is not editable per user's request; ignore any value

        if birth_date:
            try:
                d = datetime.strptime(birth_date, '%Y-%m-%d').date()
                if d < date(1900, 1, 1) or d > date.today():
                    errors['birth_date'] = "La date de naissance doit être entre 1900-01-01 et aujourd’hui."
                if profile is None:
                    from .models import Profile
                    profile = Profile.objects.create(user=request.user, birth_date=d)
                else:
                    profile.birth_date = d
            except Exception:
                errors['birth_date'] = "Date de naissance invalide (format YYYY-MM-DD)."
        # if there are any errors, render template with errors and keep inputs visible
        if errors:
            return render(request, 'frontend/profile.html', {'profile': profile, 'errors': errors})

        request.user.save()
        if profile is not None:
            profile.save()
        messages.success(request, 'Profil mis à jour avec succès.')
        return redirect('profile')

    return render(request, 'frontend/profile.html', {'profile': profile})

def delete_account(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        user = request.user
        logout(request)
        try:
            user.delete()
            messages.success(request, "Votre compte a été supprimé.")
        except Exception:
            messages.error(request, "Impossible de supprimer le compte pour le moment.")
        return redirect('login')
    # Forbid GET deletion; just redirect back to profile
    messages.error(request, "Action non autorisée.")
    return redirect('profile')
