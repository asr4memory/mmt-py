from django.forms import ModelForm, RadioSelect
from django.contrib.auth.forms import BaseUserCreationForm, UsernameField
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()


class RegisterForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        field_classes = {
            "username": UsernameField,
        }


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "locale"]
        widgets = {
            "locale": RadioSelect(),
        }
