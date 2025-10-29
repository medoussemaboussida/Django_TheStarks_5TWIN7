from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import SignupForm, AuthForm

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
        form = AuthForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('root')
        else:
            messages.error(request, 'Identifiants invalides')
    else:
        form = AuthForm(request)
    return render(request, 'admin/login.html', {'form': form})

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
