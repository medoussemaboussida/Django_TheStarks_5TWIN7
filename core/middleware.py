from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """Redirect unauthenticated users to LOGIN_URL except for whitelisted paths."""

    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that should remain publicly accessible
        self.allow_exact = {
            settings.LOGIN_URL,
            reverse('login') if 'login' else '/login/',
            reverse('password_reset'),
            reverse('password_reset_done'),
            reverse('password_reset_complete'),
        }
        # Prefixes to skip (static, media, admin, password reset confirm with dynamic parts)
        self.allow_prefix = (
            '/static/',
            '/media/',
            '/admin/',
            '/reset/',  # includes reset/<uidb64>/<token>/
            '/favicon.ico',
        )
        # Also allow register if present
        try:
            self.allow_exact.add(reverse('register'))
        except Exception:
            pass

    def __call__(self, request):
        path = request.path
        if not request.user.is_authenticated:
            if (path not in self.allow_exact) and (not path.startswith(self.allow_prefix)):
                return redirect(settings.LOGIN_URL)
        return self.get_response(request)
