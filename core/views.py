from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
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
    return render(request, 'frontend/profile.html')
