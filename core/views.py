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
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models.functions import TruncMonth
from django.db.models import Count, Q
from django.utils import timezone
import json
import json
import urllib.parse
import urllib.request
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

def admin_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_staff:
        messages.error(request, "Accès refusé.")
        return redirect('root')
    users = User.objects.all().order_by('-date_joined')
    now = timezone.now().date().replace(day=1)
    ym = []
    y, m = now.year, now.month
    for _ in range(12):
        ym.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    ym.reverse()
    monthly_qs = User.objects.annotate(mm=TruncMonth('date_joined')).values('mm').annotate(c=Count('id'))
    monthly_map = {item['mm'].date(): item['c'] for item in monthly_qs if item['mm']}
    month_labels = [f"{yy}-{mm:02d}" for (yy, mm) in ym]
    from datetime import date as _date
    month_counts = [monthly_map.get(_date(yy, mm, 1), 0) for (yy, mm) in ym]
    total_users = users.count()
    admin_count = User.objects.filter(is_superuser=True).count()
    utilisateur_count = max(total_users - admin_count, 0)
    chart_ctx = {
        'chart_month_labels': json.dumps(month_labels),
        'chart_month_counts': json.dumps(month_counts),
        'chart_roles_labels': json.dumps(['Admin', 'Utilisateur']),
        'chart_roles_counts': json.dumps([admin_count, utilisateur_count]),
    }

    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        if action == 'add':
            # Handle Add User form submission
            username = request.POST.get('au_username', '').strip()
            email = request.POST.get('au_email', '').strip()
            password = request.POST.get('au_password', '')
            is_staff = bool(request.POST.get('au_is_staff'))
            is_superuser = bool(request.POST.get('au_is_superuser'))

            au_errors = {}
            if not re.fullmatch(r'[A-Za-z0-9._-]{3,30}', username):
                au_errors['au_username'] = "Nom d’utilisateur invalide (3-30 caractères, lettres/chiffres . _ -)."
            elif User.objects.filter(username__iexact=username).exists():
                au_errors['au_username'] = "Ce nom d’utilisateur est déjà pris."

            if not password:
                au_errors['au_password'] = "Mot de passe requis."
            else:
                try:
                    validate_password(password)
                except ValidationError as ve:
                    au_errors['au_password'] = ' '.join(ve.messages)

            if au_errors:
                ctx = {
                    'users': users,
                    'au_errors': au_errors,
                    'open_add_user': True,
                    'au_values': {
                        'au_username': username,
                        'au_email': email,
                        'au_is_staff': is_staff,
                        'au_is_superuser': is_superuser,
                    }
                }
                ctx.update(chart_ctx)
                return render(request, 'admin/index.html', ctx)

            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser if request.user.is_superuser else False
            user.save()
            messages.success(request, 'Utilisateur ajouté avec succès.')
            return redirect('admin_dashboard')

        elif action == 'edit':
            uid = request.POST.get('eu_user_id')
            try:
                target = User.objects.get(pk=uid)
            except User.DoesNotExist:
                messages.error(request, "Utilisateur introuvable.")
                return redirect('admin_dashboard')

            username = request.POST.get('eu_username', '').strip()
            email = request.POST.get('eu_email', '').strip()
            password = request.POST.get('eu_password', '')
            is_staff = bool(request.POST.get('eu_is_staff'))
            is_superuser = bool(request.POST.get('eu_is_superuser'))

            eu_errors = {}
            if not re.fullmatch(r'[A-Za-z0-9._-]{3,30}', username):
                eu_errors['eu_username'] = "Nom d’utilisateur invalide (3-30 caractères, lettres/chiffres . _ -)."
            elif User.objects.filter(username__iexact=username).exclude(pk=target.pk).exists():
                eu_errors['eu_username'] = "Ce nom d’utilisateur est déjà pris."

            if password:
                try:
                    validate_password(password, user=target)
                except ValidationError as ve:
                    eu_errors['eu_password'] = ' '.join(ve.messages)

            # Protections
            if target.is_superuser and not request.user.is_superuser:
                messages.error(request, "Action non autorisée sur un administrateur.")
                return redirect('admin_dashboard')

            if eu_errors:
                ctx = {
                    'users': users,
                    'eu_errors': eu_errors,
                    'open_edit_user': True,
                    'edit_user_id': target.pk,
                    'eu_values': {
                        'eu_username': username or target.username,
                        'eu_email': email or target.email,
                        'eu_is_staff': is_staff if 'eu_is_staff' in request.POST else target.is_staff,
                        'eu_is_superuser': is_superuser if 'eu_is_superuser' in request.POST else target.is_superuser,
                    }
                }
                ctx.update(chart_ctx)
                return render(request, 'admin/index.html', ctx)

            target.username = username
            target.email = email
            target.is_staff = is_staff
            if request.user.is_superuser:
                target.is_superuser = is_superuser
            if password:
                target.set_password(password)
            target.save()
            messages.success(request, 'Utilisateur mis à jour.')
            return redirect('admin_dashboard')

        elif action == 'delete':
            uid = request.POST.get('du_user_id')
            try:
                target = User.objects.get(pk=uid)
            except User.DoesNotExist:
                messages.error(request, "Utilisateur introuvable.")
                return redirect('admin_dashboard')

            if str(request.user.pk) == str(uid):
                messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
                return redirect('admin_dashboard')
            if target.is_superuser and not request.user.is_superuser:
                messages.error(request, "Action non autorisée sur un administrateur.")
                return redirect('admin_dashboard')

            target.delete()
            messages.success(request, 'Utilisateur supprimé.')
            return redirect('admin_dashboard')

        elif action == 'report':
            # Generate a PDF report of monthly signups
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import mm
                from io import BytesIO

                buffer = BytesIO()
                pdf = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                title = "Rapport: Inscriptions par mois (12 derniers mois)"
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawString(20*mm, height - 20*mm, title)

                pdf.setFont("Helvetica", 10)
                y = height - 30*mm
                pdf.drawString(20*mm, y, f"Généré le: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
                y -= 12

                # Table header
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(20*mm, y, "Mois")
                pdf.drawString(100*mm, y, "Inscriptions")
                y -= 8
                pdf.line(20*mm, y, 190*mm, y)
                y -= 6
                pdf.setFont("Helvetica", 10)

                for label, count in zip(json.loads(chart_ctx['chart_month_labels']), json.loads(chart_ctx['chart_month_counts'])):
                    if y < 20*mm:
                        pdf.showPage()
                        y = height - 20*mm
                        pdf.setFont("Helvetica-Bold", 11)
                        pdf.drawString(20*mm, y, "Mois")
                        pdf.drawString(100*mm, y, "Inscriptions")
                        y -= 8
                        pdf.line(20*mm, y, 190*mm, y)
                        y -= 6
                        pdf.setFont("Helvetica", 10)
                    pdf.drawString(20*mm, y, str(label))
                    pdf.drawString(100*mm, y, str(count))
                    y -= 12

                pdf.showPage()
                pdf.save()
                buffer.seek(0)

                from django.http import HttpResponse
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="rapport_inscriptions_mensuelles.pdf"'
                return response
            except Exception:
                messages.error(request, "La génération du PDF nécessite la bibliothèque 'reportlab'. Exécutez: pip install reportlab")
                return redirect('admin_dashboard')

    # Filtering and sorting for users table (GET only)
    search_q = request.GET.get('q', '').strip()
    order_key = request.GET.get('order', '-date')
    order_by = '-date_joined' if order_key == '-date' else 'date_joined'
    users_list = users
    if search_q:
        users_list = users_list.filter(Q(username__icontains=search_q) | Q(email__icontains=search_q))
    users_list = users_list.order_by(order_by)

    ctx = {
        'users': users_list,
        'q': search_q,
        'order': order_key,
    }
    ctx.update(chart_ctx)
    return render(request, 'admin/index.html', ctx)

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
        photo = request.FILES.get('photo')

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

        # Photo upload handling
        if photo is not None:
            # Ensure profile exists before assigning photo
            if profile is None:
                from .models import Profile
                profile = Profile.objects.create(user=request.user)
            content_type = getattr(photo, 'content_type', '') or ''
            size = getattr(photo, 'size', 0) or 0
            if not content_type.startswith('image/'):
                errors['photo'] = "Le fichier doit être une image (JPEG, PNG, GIF, ...)."
            elif size > 2 * 1024 * 1024:
                errors['photo'] = "L’image est trop volumineuse (max 2 Mo)."
            else:
                profile.photo = photo
        # if there are any errors, render template with errors and keep inputs visible
        if errors:
            return render(request, 'frontend/profile.html', {'profile': profile, 'errors': errors})

        request.user.save()
        if profile is not None:
            profile.save()
        messages.success(request, 'Profil mis à jour avec succès.')
        return redirect('profile')

    # GET request: render the profile page
    return render(request, 'frontend/profile.html', {'profile': profile})

@csrf_exempt
def grok_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}
    messages = data.get('messages') or []
    prompt = data.get('prompt')
    if not messages and prompt:
        messages = [{'role': 'user', 'content': prompt}]
    if not messages:
        return JsonResponse({'error': 'messages or prompt required'}, status=400)

    api_key = getattr(settings, 'GROK_API_KEY', '')
    # Default to Groq endpoint unless overridden in env
    api_base = getattr(settings, 'GROK_API_BASE', 'https://api.groq.com/openai/v1')
    if not api_key:
        return JsonResponse({'error': 'Server missing GROK_API_KEY'}, status=500)

    # Align with user's working params
    model = data.get('model', 'llama-3.3-70b-versatile')
    payload = {
        'model': model,
        'messages': messages,
        'temperature': data.get('temperature', 0.5),
        'max_tokens': data.get('max_tokens', 512),
        'stream': False,
    }
    try:
        req = urllib.request.Request(
            api_base.rstrip('/') + '/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            out = json.loads(body)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode('utf-8')
        except Exception:
            err_body = ''
        info = {'error': 'Upstream API error', 'status': e.code}
        if settings.DEBUG:
            info['details'] = err_body
        # For Groq, no special fallback unless client requests another
        if model != 'llama-3.3-70b-versatile':
            return JsonResponse(info, status=502)
        try:
            payload['model'] = 'llama-3.1-8b-instant'
            req = urllib.request.Request(
                api_base.rstrip('/') + '/chat/completions',
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode('utf-8')
                out = json.loads(body)
        except Exception:
            return JsonResponse(info, status=502)
    except Exception as e:
        info = {'error': 'Upstream API error'}
        if settings.DEBUG:
            info['details'] = str(e)
        return JsonResponse(info, status=502)

    reply = ''
    try:
        reply = (out.get('choices') or [{}])[0].get('message', {}).get('content', '')
    except Exception:
        reply = ''
    return JsonResponse({'reply': reply, 'raw': out})

def change_password(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        messages.error(request, 'Action non autorisée.')
        return redirect('profile')

    current_password = request.POST.get('current_password', '')
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')

    field_errors = {}
    # Verify current password
    if not request.user.check_password(current_password):
        field_errors['current_password'] = 'Mot de passe actuel incorrect.'

    # New vs confirm
    if new_password != confirm_password:
        field_errors['confirm_password'] = 'La confirmation ne correspond pas.'

    # Strength/validators
    if not field_errors:
        try:
            validate_password(new_password, user=request.user)
        except ValidationError as ve:
            field_errors['new_password'] = ' '.join(ve.messages)

    if field_errors:
        # Re-render profile with errors and keep change password modal open via flag
        profile = getattr(request.user, 'profile', None)
        return render(request, 'frontend/profile.html', {
            'profile': profile,
            'pw_errors': field_errors,
            'open_change_password': True,
        })

    # All good: set password
    request.user.set_password(new_password)
    request.user.save()
    messages.success(request, 'Mot de passe modifié avec succès. Connectez-vous à nouveau.')
    return redirect('login')

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
