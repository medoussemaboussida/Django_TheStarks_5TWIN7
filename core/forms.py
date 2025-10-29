from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Profile

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    birth_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

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
        # birth_date styling
        if 'birth_date' in self.fields:
            self.fields['birth_date'].widget.attrs.update({
                'class': 'form-control form-control-user',
                'placeholder': 'Birth date (optional)'
            })
        # light client hints
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({'minlength': '6'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'minlength': '6'})
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({'minlength': '4'})

class AuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'Username',
            'minlength': '4',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-user',
            'placeholder': 'Password',
            'minlength': '6',
        })
