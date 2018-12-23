from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UsernameField
from django.forms import ClearableFileInput

from hasker.forms import BootstrapForm
from .models import User

from django.utils.translation import gettext_lazy as _


class ImageInput(ClearableFileInput):
    template_name = 'user/widgets/image_input.html'


class SignUpForm(UserCreationForm, BootstrapForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'avatar']
        widgets = {
            'avatar': ImageInput()
        }


class UserProfileForm(BootstrapForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'avatar']
        widgets = {
            'avatar': ImageInput()
        }


class LoginForm(AuthenticationForm):
    username = UsernameField(widget=forms.TextInput(attrs={
        'autofocus': True,
        'class': 'form-control'
    }))
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        }),
    )
