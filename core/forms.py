from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False, max_length=150)
    last_name = forms.CharField(required=False, max_length=150)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        # Ensure normal users by default; admin accounts should be created by superuser
        user.is_staff = False
        if commit:
            user.save()
        return user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply SB Admin 2 styles and placeholders
        widgets = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name (optional)',
            'last_name': 'Last Name (optional)',
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
