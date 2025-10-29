from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import SetPasswordForm
from .models import Profile
from datetime import date

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    birth_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2",)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        # Ensure normal users by default; admin accounts should be created by superuser
        user.is_staff = False
        if commit:
            user.save()
            # create or update profile with birth_date
            Profile.objects.update_or_create(user=user, defaults={'birth_date': self.cleaned_data.get('birth_date')})
        return user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply SB Admin 2 styles and placeholders
        widgets = {
            'username': 'Username',
            'email': 'Email Address',
            'password1': 'Password',
            'password2': 'Repeat Password',
        }
        for name, placeholder in widgets.items():
            if name in self.fields:
                field = self.fields[name]
                field.widget.attrs.update({
                    'class': 'form-control form-control-user',
                    'placeholder': placeholder,
                })
                # remove default help_text and set required message
                field.help_text = ''
                errs = field.error_messages
                errs['required'] = 'Ce champ est obligatoire.'
                if name == 'username':
                    errs['invalid'] = "Nom d’utilisateur invalide."
                if name == 'password2':
                    errs['password_mismatch'] = 'Les mots de passe ne correspondent pas.'
        # birth_date styling
        if 'birth_date' in self.fields:
            self.fields['birth_date'].widget.attrs.update({
                'class': 'form-control form-control-user',
                'placeholder': 'Birth date',
            })
            self.fields['birth_date'].help_text = ''
            self.fields['birth_date'].error_messages['required'] = 'Ce champ est obligatoire.'
        # no native minlength; rely on server validation and strength meter

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ce nom d’utilisateur est déjà pris.")
        return username

    def clean_birth_date(self):
        bd = self.cleaned_data.get('birth_date')
        if bd and bd > date.today():
            raise forms.ValidationError("La date de naissance ne peut pas être dans le futur.")
        return bd

    def clean(self):
        cleaned = super().clean()
        pwd = cleaned.get('password1')
        if pwd:
            has_lower = any(c.islower() for c in pwd)
            has_upper = any(c.isupper() for c in pwd)
            has_digit = any(c.isdigit() for c in pwd)
            has_symbol = any(not c.isalnum() for c in pwd)
            if len(pwd) < 8 or sum([has_lower, has_upper, has_digit, has_symbol]) < 3:
                self.add_error('password1', "Mot de passe trop faible. Min 8 caractères et au moins 3 types: minuscule, majuscule, chiffre, symbole.")
        # custom mismatch message
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        return cleaned

class AuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'Username',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'Password',
        })

class EmailAuthForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(strip=False, widget=forms.PasswordInput)

    error_messages = {
        'invalid_login': "Email ou mot de passe incorrect.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = None
        self.fields['email'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'Email Address',
        })

class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'New password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'Confirm new password',
        })

    def get_user(self):
        return self.user_cache

class PasswordResetRequestForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'Email Address',
        })
