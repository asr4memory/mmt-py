from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        "username",
        "email",
        "is_active",
        "profile__full_name",
        "profile__locale",
    ]
    inlines = [ProfileInline]
    actions = ["make_active"]

    @admin.action(description=_("Activate selected users"))
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        # TODO: Send email to each user separately.
